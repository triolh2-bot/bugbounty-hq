from bugbountyhq import create_app


app = create_app()


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    print(f"🔓 BugBountyHQ running on http://localhost:{port}")
    app.run(debug=False, port=port, host="0.0.0.0")
