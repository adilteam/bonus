import os
from app import app

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(127.0.0.1("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
