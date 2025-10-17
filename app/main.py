from __init__ import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

## Run Note ##
# Environment Activation: ./venv/Scripts/activate
# Localhost Address: http://127.0.0.1:5000/
