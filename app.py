from flask_openapi3 import OpenAPI, Info


from routes.routes import transcripe_blueprint

info = Info(title="TranscriptionService API", version="1.0")
app = OpenAPI(__name__, info=info)

app.register_blueprint(transcripe_blueprint)


if __name__ == '__main__':
    app.run(debug=True)
