import os

import uvicorn

if __name__ == "__main__":
    # Defaults entsprechen dem bisherigen lokalen Dev-Betrieb (127.0.0.1:8000
    # mit Auto-Reload). Auf dem Server wird der Dienst dagegen über systemd
    # direkt mit uvicorn gestartet (siehe deploy/) — dieses Skript dient dort
    # nur noch zum manuellen Testen auf einem abweichenden Port.
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "1") == "1",
    )
