import uvicorn
import os
import sys

if __name__ == "__main__":
    # Force UTF-8 output encoding for Windows terminal compatibility
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    
    print("\n" + "="*60)
    print(f" Starting NEXORA AI (Python + FastAPI + MongoDB)")
    print(f" Server running at: http://{host}:{port}")
    print("="*60 + "\n")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True)

