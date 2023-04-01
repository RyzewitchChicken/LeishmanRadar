from pymongo import MongoClient
import certifi

MONGO_URI= 'mongodb+srv://Leishman:<ponlepassword>@leishmandb.xvtamoi.mongodb.net/?retryWrites=true&w=majority'
ca= certifi.where()


def dbConnection():
    try: 
        client=MongoClient(MONGO_URI,tlsCAFile=ca)
        db =client["leishmanDB"]
    except ConnectionError:
        print('Error de conexion')
    return db        
