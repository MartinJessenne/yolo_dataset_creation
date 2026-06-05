import marimo as mo
    app = mo.App()
  
    @app.cell
    def __():
        import sys
        print(f"Active Python interpreter: {sys.version}")
        return
  
    if __name__ == "__main__":
        app.run()
