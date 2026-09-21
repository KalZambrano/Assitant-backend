TOOL_DEFINITIONS = [
    {
        "name": "actualizar_contacto_en_crm",
        "description": "Crea o actualiza un contacto del CRM simulado usando nombre, empresa, email y datos verificados del correo.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nombre completo del contacto."},
                "company": {"type": "string", "description": "Empresa del contacto."},
                "email": {"type": "string", "description": "Email válido del contacto; es la clave de coincidencia."},
                "phone": {"type": "string", "description": "Teléfono si está disponible."},
                "status": {"type": "string", "description": "Estado comercial si está explícitamente indicado."},
            },
            "required": ["email"],
        },
    },
    {
        "name": "agendar_reunion_en_calendar",
        "description": "Crea una reunión en el Calendar local simulado. Requiere fecha y hora específicas; nunca las inventes.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Título de la reunión."},
                "contact_id": {"type": "integer", "description": "ID del contacto asociado, si existe."},
                "date": {"type": "string", "description": "Fecha ISO YYYY-MM-DD."},
                "time": {"type": "string", "description": "Hora HH:MM o HH:MM:SS."},
                "duration_minutes": {"type": "integer", "description": "Duración positiva en minutos; por defecto 30."},
                "description": {"type": "string", "description": "Descripción de la reunión."},
            },
            "required": ["title", "date", "time"],
        },
    },
]
