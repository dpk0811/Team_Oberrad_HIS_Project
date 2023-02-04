from flask import Flask,render_template, make_response

app=Flask(__name__,template_folder='template')
app.config['SESSION_COOKIE_HTTPONLY']=False
app.secret_key='abc' 


@app.route("/")
def home():
    resp = make_response(render_template('base.html'))
    #resp.set_cookie('session', '.eJyrViotTi1SsqpWSs0tyMmvTE1VskpLzClO1VHKyU9PT03JzMtMUbKyQHDzEnOBapQSExMVgFipthYAIw0XTQ.Y94oQg.2r2H46esUFO0enaOpz6_x-827wo.eJyrViotTi1SsqpWSs0tyMmvTE1VskpLzClO1VHKyU9PT03JzMtMUbKyQHDzEnOBapQSExMVgFipthYAIw0XTQ.Y94oQg.2r2H46esUFO0enaOpz6_x-827wo')
    return resp


if __name__=="__main__":
    app.run(debug=True)



