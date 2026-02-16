from __future__ import annotations

import logging
import re
from typing import Any

from catchdash_worker.config import settings
from catchdash_worker.queue.backend_api import BackendQueueAPI
from catchdash_worker.tts.extraction import extract_main_text
from catchdash_worker.tts.llm import summarize_with_llm
from catchdash_worker.tts.synth import synthesize_with_kokoro

logger = logging.getLogger(__name__)


def run_job(api: BackendQueueAPI, job: dict[str, Any]) -> None:
    job_id = str(job.get('id'))
    job_type = job.get('type')
    topic_id = str(job.get('topic_id'))
    item_id = str(job.get('item_id'))

    try:
        api.update_job(job_id, {'status': 'processing', 'progress': 8, 'message': 'loading item'})
        item = api.get_topic_item(topic_id, item_id)

        api.update_job(job_id, {'status': 'processing', 'progress': 22, 'message': 'extracting article'})
        full_text = extract_main_text(item['url'], timeout_seconds=settings.http_timeout_seconds)
        if not full_text:
            raise RuntimeError('extraction produced empty text')

        tts_text = full_text
        if job_type == 'tts_summary':
            api.update_job(job_id, {'status': 'processing', 'progress': 34, 'message': 'summarizing with llm'})

            def _on_chunk(meta: dict[str, Any]) -> None:
                chunk_count = int(meta.get('chunk_count') or 0)
                if chunk_count <= 0 or chunk_count % 8 != 0:
                    return
                # Move summary phase from 34 to 52 in small increments.
                progress = min(52, 34 + (chunk_count // 8))
                api.update_job(job_id, {'status': 'processing', 'progress': progress, 'message': 'summarizing with llm'})

            provider = settings.llm_provider
            model = settings.llm_model
            base_url = settings.llm_base_url
            api_key = settings.llm_api_key
            if provider == 'ollama':
                base_url = base_url or settings.ollama_base_url
                model = model or settings.ollama_model

            summary = summarize_with_llm(
                provider=provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
                title=item.get('title', 'Untitled'),
                text=full_text,
                timeout_seconds=settings.llm_timeout_seconds,
                max_input_chars=settings.summary_input_chars,
                on_chunk=_on_chunk,
            )
            if not summary:
                raise RuntimeError('llm returned empty summary')
            tts_text = summary[: settings.summary_char_limit]

        api.update_job(job_id, {'status': 'processing', 'progress': 60, 'message': 'synthesizing audio'})
        clean_title = _sanitize_for_tts(item.get('title', 'Untitled'))
        clean_tts_text = _sanitize_for_tts(tts_text)
        script = f"{clean_title}. {clean_tts_text}"
        script = script[: settings.max_tts_chars]
        audio_bytes, mime = synthesize_with_kokoro(
            base_url=settings.kokoro_base_url,
            text=script,
            voice=settings.tts_voice,
            timeout_seconds=settings.tts_timeout_seconds,
        )

        api.update_job(job_id, {'status': 'processing', 'progress': 84, 'message': 'uploading audio'})
        upload = api.upload_job_audio(job_id, audio_bytes, mime)
        api.update_job(
            job_id,
            {
                'status': 'ready',
                'progress': 100,
                'message': 'ready',
                'output_ref': upload.get('output_ref'),
            },
        )
        logger.info('job=%s ready topic=%s item=%s', job_id, topic_id, item_id)
    except Exception as exc:
        api.update_job(job_id, {'status': 'failed', 'progress': 100, 'message': str(exc)})
        logger.exception('job=%s failed err=%s', job_id, exc)


def _sanitize_for_tts(text: str) -> str:
    value = str(text or "")
    # Remove markdown/control symbols and keep speech-friendly punctuation.
    value = re.sub(r"[*_`~#|<>[\]{}\\^=+]", " ", value)
    # Remove punctuation that tends to sound noisy in TTS.
    value = re.sub(r"[@$%&]+", " ", value)
    # Collapse repeated punctuation (!!!, ???, ...) to a single mark.
    value = re.sub(r"([.!?,;:])\1+", r"\1", value)
    # Normalize whitespace and spacing around punctuation.
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+([,.!?;:])", r"\1", value)
    return value
