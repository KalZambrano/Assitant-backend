# UTP Assistant — Backend

Backend local MVP para procesar correos, analizar su contenido con Gemini u Ollama y ejecutar herramientas simuladas de CRM y Calendar.

## Inicio rápido

```powershell
uv sync
Copy-Item .env.example .env
uv run uvicorn app.main:app --reload
```

La documentación queda disponible en <http://localhost:8000/docs>.

Por defecto se usa Ollama con `llama3.2:1b`. Para Gemini, configura `AI_PROVIDER=gemini` y `GEMINI_API_KEY`.
