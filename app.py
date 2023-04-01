from flask import Flask, request, render_template, Response, jsonify, redirect, url_for, session,make_response, send_file,render_template_string
import pickle
import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objs as go
import plotly
import plotly.express as xp
import plotly.offline as pyo
import database as dbase
from  user import User
from prediction import Prediction
from bson.json_util import dumps
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from xhtml2pdf import pisa
import io
import base64

db=dbase.dbConnection()

app= Flask(__name__)
app.secret_key = "mysecretkey"

model=pickle.load(open('rf_model.pkl','rb'))



@app.route('/prediction/<int:npred>',methods=['GET'])
def getnpred(npred):
    datapred=[]
    prediction_ahead=db['prediction_ahead']
    for cs in prediction_ahead.find({},{'_id':False}):
        values=list(cs.values())
        datapred.append(values)
    res=model.predict(datapred)
    
    return list(res[:npred])

## Prediccion data
@app.route('/data')
def getdata():
    datapred=[]
    prediction_ahead=db['prediction_ahead']
    for cs in prediction_ahead.find({},{'_id':False}):
        values=list(cs.values())
        datapred.append(values)
    
    return jsonify(datapred)


## Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
def index():
    predictions=db['prediction']
    casesdata=predictions.find()

    graphJSON=grafico()
    #data = GraficoInteractivo('2015-12-27','2022-10-02')
    pred=getnpred(1)
    return render_template('index.html', predictions=casesdata,graphJSON=graphJSON)



@app.route('/generate-pdf/<int:npred>',methods=['POST'])
def generate_pdf(npred):
    collection=db['prediction']
    last_data = collection.find_one(sort=[("data_iniSE", -1)])
    init_Date=last_data.get('data_iniSE')
    init_case=[last_data.get('casos')]
    # process the data here
    weekly_dates = [init_Date + timedelta(weeks=x) for x in range(npred+1)]
    print(weekly_dates)
    pred=getnpred(npred)
    print(pred)

    x=weekly_dates
    y=init_case + pred
    fig = go.Figure(layout=go.Layout(title='Predicciones',yaxis=dict(title='n° casos'),xaxis=dict(title='Fecha')))    
    fig.add_trace(go.Scatter(x=x, y=y))

    img_buf = io.BytesIO()
    fig.write_image(img_buf, format='png')
    img_buf.seek(0)
    Date_List = [x.strftime('%Y-%m-%d') for x in x]
    # Convert the image buffer to a base64-encoded string
    img_data = base64.b64encode(img_buf.getvalue()).decode('utf-8')
    table_data = [['Fecha', 'Prediccion']] + list(zip(Date_List, y))
    # Generate the HTML content for the PDF
    date = datetime.now()
    stdate=date.strftime( '%Y-%m-%d')
    rendered_html = render_template_string("{% extends 'content.html' %}", table_data=table_data, img_data=img_data,stdate=stdate)
    # Generate the PDF
    pdf_buf = io.BytesIO()
    pisa.CreatePDF(io.StringIO(rendered_html), dest=pdf_buf)

    # Set the buffer's position to the beginning
    pdf_buf.seek(0)

    # Return the PDF file as a Flask response
    response = make_response(pdf_buf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=plot.pdf'
    return response




@app.route('/button', methods=['POST'])
def get_button_status():
    selected_option = request.json['mySelect']
    if selected_option != 'default':
        show_button= True
    else:
        show_button= False
    print(selected_option)
    return jsonify({'show_button': show_button})

@app.route('/graficopred/<int:npred>',methods=['GET','POST'])
def graficopred(npred):
    collection=db['prediction']
    last_data = collection.find_one(sort=[("data_iniSE", -1)])
    init_Date=last_data.get('data_iniSE')
    init_case=[last_data.get('casos')]
    # process the data here
    weekly_dates = [init_Date + timedelta(weeks=x) for x in range(npred+1)]
    print(weekly_dates)
    pred=getnpred(npred)
    print(pred)
    

    x=weekly_dates
    y=init_case + pred
    print(y)
    #trace=go.Scatter(x=x, y=y, mode='lines')
    fig = go.Figure(
        data=[go.Scatter(x=x, y=y, mode='lines+markers', name='prediccion')]
        )
    
    # Update the chart in the HTML and return it
    return fig.to_json()


@app.route('/grafico')
def grafico():
    collection = db['prediction']

    data = []
    for item in collection.find():
        data.append(item)
    x = [item['data_iniSE'] for item in data]
    y = [item['casos'] for item in data]
    print(y)
    fig = go.Figure(layout=go.Layout(title='Número de casos de Leishmaniasis 2018 - 2022',yaxis=dict(title='n° casos'),xaxis=dict(title='Semana Epidemiologica')))
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines',name='casos'))
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


@app.route('/chart', methods=['GET','POST'])
def chart():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = db.prediction.find({'data_iniSE': {'$gte': datetime.strptime(start_date, '%Y-%m-%d'), '$lte': datetime.strptime(end_date, '%Y-%m-%d')}})
    x = []
    y = []
    for item in data:
        x.append(item['data_iniSE'])
        y.append(item['casos'])
    # Create the chart object
    fig = go.Figure(
        data=[go.Scatter(x=x, y=y)],
        layout=go.Layout(title='Número de casos de Leishmaniasis 2018 - 2022',yaxis=dict(title='n° casos'),xaxis=dict(title='Semana Epidemiologica'))
    )
    # Return the chart data as JSON
    return fig.to_json()

## Login View
@app.route('/')
def login():
    return render_template('login.html')

## Register Viz
@app.route('/register')
def register():
    return render_template('register.html')

## Registro Form
@app.route('/registro',methods=['POST'])
def registro():
    users=db['users']
    name=request.form['name']
    email=request.form['email']
    username=request.form['username']
    password=request.form['password']

    if users.find_one({'email': email}):
        error = 'Usuario ya existe.'
    elif name and email and username and password:
        user=User(name, email, password, username)
        users.insert_one(user.toDBCollection())
        response= jsonify({
            'name': name,
            'email': email,
            'password': password,
            'username':username
        })

        return redirect(url_for('login'))

    return render_template('register.html',error=error)

### Login Form
@app.route('/loginin', methods=['GET', 'POST'])
def loginin():
    users=db['users']
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})
        if user:
            if (user['password'] == password):
                session['username'] = username
                return redirect(url_for('index'))
        else:
            error = 'Usuario y/o contraseña incorrectos. Intente de nuevo.'
            return render_template('login.html', error=error)    


## Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))





@app.errorhandler(404)
def notFound(error=None):
    message ={
        'message': 'No encontrado ' + request.url,
        'status': '404 Not Found'
    }
    response = jsonify(message)
    response.status_code = 404
    return response


if __name__ =='__main__':
    app.run(debug=True)

