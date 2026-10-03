import io
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/audio", tags=["audio"])


class TTSIn(BaseModel):
    text: str
    lang: str = "en"
    voice: Optional[str] = None


def _silent_wav(duration_ms: int = 200) -> bytes:
    sample_rate = 22050
    num_samples = sample_rate * duration_ms // 1000
    data_size = num_samples * 2
    header = (
        b"RIFF" + (36 + data_size).to_bytes(4, "little") + b"WAVEfmt "
        + (16).to_bytes(4, "little") + (1).to_bytes(2, "little")
        + (1).to_bytes(2, "little") + sample_rate.to_bytes(4, "little")
        + (sample_rate * 2).to_bytes(4, "little") + (2).to_bytes(2, "little")
        + (16).to_bytes(2, "little") + b"data" + data_size.to_bytes(4, "little")
    )
    return header + b"\x00" * data_size


@router.post("/stt")
async def stt(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Could not read audio: {e}")
    transcript = ""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(raw)
            path = f.name
        try:
            try:
                import whisper_timestamped as whisper
                model = whisper.load_model("tiny")
                res = model.transcribe(path, language=language, fp16=False)
                transcript = res.get("text", "") or ""
            except Exception:
                try:
                    import whisper
                    model = whisper.load_model("tiny")
                    res = model.transcribe(path, fp16=False)
                    transcript = res.get("text", "") or ""
                except Exception:
                    transcript = ""
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
    except Exception:
        transcript = ""
    if not transcript:
        transcript = (
            f"(Placeholder transcript — whisper unavailable) Audio received "
            f"({len(raw)} bytes, language={language}). Install whisper-timestamped for real transcription."
        )
    return {
        "filename": file.filename,
        "language": language,
        "transcript": transcript,
        "segments": [],
    }


@router.post("/tts")
async def tts(data: TTSIn):
    text = (data.text or "").strip()
    if not text:
        raise HTTPException(400, "Empty text")
    lang = (data.lang or "en").lower()[:2]
    audio_bytes: bytes = b""
    media_type = "audio/wav"
    try:
        import asyncio
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural" if lang != "hi" else "hi-IN-SwaraNeural")
            chunks = []
            async def collect():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
            asyncio.run(collect())
            if chunks:
                audio_bytes = b"".join(chunks)
                media_type = "audio/mpeg"
        except Exception:
            try:
                from gtts import gTTS
                buf = io.BytesIO()
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.write_to_fp(buf)
                audio_bytes = buf.getvalue()
                media_type = "audio/mpeg"
            except Exception:
                audio_bytes = b""
    except Exception:
        audio_bytes = b""
    if not audio_bytes:
        audio_bytes = _silent_wav(400)
        media_type = "audio/wav"
    return Response(content=audio_bytes, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename=tts.{media_type.split('/')[1]}",
        "X-TTS-Lang": data.lang,
        "X-Text-Length": str(len(text)),
    })
