
import json
import zipfile
import pandas as pd
from io import StringIO
import pymongo
from persiantools.jdatetime import JalaliDate
import datetime
from Login import adminCheck
from sklearn.linear_model import LinearRegression
from Login import decrypt , encrypt, SendSms
import random
import requests
from Login import VerificationPhone , decrypt, encrypt
from ast import literal_eval

client = pymongo.MongoClient()
farasahmDb = client['farasahm2']

def applynationalcode(data):
    textCaptcha = decrypt(data['captchaCode'][2:-1].encode())
    if textCaptcha!=data['UserInput']['captcha']:
        return json.dumps({'replay':False,'msg':'کد تصویر صحیح نیست'})
    registerNoBours = farasahmDb['registerNoBours'].find_one({'کد ملی':data['UserInput']['nationalCode']})
    if registerNoBours != None:
        VerificationPhone(registerNoBours['شماره تماس'])
        return json.dumps({'replay':True,'status':'Registered'})
    register = farasahmDb['register'].find_one({'کد ملی':int(data['UserInput']['nationalCode']),'symbol':'visa'})
    if register != None:
        daraRegister = farasahmDb['daraRegister'].find_one({'nationalCode':data['UserInput']['nationalCode']})
        if daraRegister == None:
            return json.dumps({'replay':True,'status':'RegisterDara'})
        else:
            VerificationPhone(daraRegister['phone'])
            return json.dumps({'replay':True,'status':'Registered'})
    return json.dumps({'replay':True,'status':'NotFund'})

def questionauth(data):
    nationalCode = data['nationalCode']
    register = pd.DataFrame(farasahmDb['register'].find({'کد ملی':{'$gt':int(nationalCode)},'symbol':'visa'}).limit(150))
    if len(register)<30:
        register = pd.DataFrame(farasahmDb['register'].find({'کد ملی':{'$lt':int(nationalCode)},'symbol':'visa'}).limit(150))
    register = register[['کد سهامداری','نام خانوادگی ','محل صدور','سری','نام پدر']]
    register = register.fillna('-')
    basic = farasahmDb['register'].find_one({'کد ملی':int(nationalCode),'symbol':'visa'},{'_id':0})

    boursiCode = list(set(register['کد سهامداری'].to_list()))[:4]
    boursiCode.append(basic['کد سهامداری'])
    random.shuffle(boursiCode)

    family = list(set(register['نام خانوادگی '].to_list()))[:4]
    family.append(basic['نام خانوادگی '])
    random.shuffle(family)


    fromm = list(set(register['محل صدور'].to_list()))[:4]
    fromm.append(basic['محل صدور'])
    random.shuffle(fromm)

    serial = list(set(register['سری'].to_list()))[:4]
    serial.append(basic['سری'])
    random.shuffle(serial)

    fatherName = list(set(register['نام پدر'].to_list()))[:4]
    fatherName.append(basic['نام پدر'])
    random.shuffle(fatherName)


    return json.dumps({'replay':True,'qustion':{"boursiCode":boursiCode,"family":family,"fromm":fromm,"serial":serial,"fatherName":fatherName}})

def applycode(data):
    apply = farasahmDb['dara_otp'].find_one({'phone':data['inputPhone']['phone']},sort=[('date', -1)])['code']
    if apply == str(data['inputPhone']['code']):
        filter_query = {'nationalCode': data['inputPhone']['nationalCode']}
        update_query = {'$set': {'phone':data['inputPhone']['phone'],'nationalCode':data['inputPhone']['nationalCode'],'dateStart':datetime.datetime.now()}}
        farasahmDb['AuthenticationSession'].update_one(filter_query, update_query, upsert=True)
        idcode = encrypt(data['inputPhone']['nationalCode']).decode()
        return json.dumps({'replay':True,'id':idcode})
    else:
        return json.dumps({'replay':False,'msg':'کد تایید صحیح نیست'})


def access(data):
    idcode = decrypt(data['id'].encode())
    acc = farasahmDb['AuthenticationSession'].find_one({'nationalCode':idcode})
    if acc == None:
        return json.dumps({'replay':False})
    else:
        return json.dumps({'replay':True})


def authenticationsession(data):
    idcode = decrypt(data['id'].encode())
    acc = farasahmDb['AuthenticationSession'].find_one({'nationalCode':idcode},{'_id':0})
    if acc == None:
        return json.dumps({'replay':False})
    NoBours = farasahmDb['registerNoBours'].find_one({'کد ملی':int(idcode)})
    register = farasahmDb['register'].find_one({'کد ملی':int(idcode)})
    if NoBours==None and register==None: return json.dumps({'replay':True,'auth':'rejected'})
    if NoBours!=None: return json.dumps({'replay':True,'auth':'approve'})
    else: return json.dumps({'replay':True,'auth':'check'})


def answerauth(data):


    dic = farasahmDb['register'].find_one({'کد ملی':int(data['nationalcod'])})

    if data['answer']['family'] != dic['نام خانوادگی ']:
        return json.dumps({'reply': False , 'msg': 'پاسخ شما درست نبود.'})

    if data['answer']['boursiCode'] != dic['کد سهامداری']:
        return json.dumps({'reply': False , 'msg': 'پاسخ شما درست نبود.'})
     
    if data['answer']['fromm'] != dic['محل صدور']:
        return json.dumps({'reply': False , 'msg': 'پاسخ شما درست نبود.'})
    if data['answer']['serial'] != dic['سری']:
        return json.dumps({'reply': False , 'msg': 'پاسخ شما درست نبود.'}) 
    if data['answer']['fatherName'] != dic['نام پدر']:
        return json.dumps({'reply': False , 'msg': 'پاسخ شما درست نبود.'})
    return json.dumps({'reply':True})


def register(data):
    VerificationPhone(data['phone'])
    return json.dumps({'replay':True})


def codeRegister(data):
    phone = data['phone']
    cheakcode = farasahmDb['VerificationPhone'].find_one({'phone':phone})
    if cheakcode['code'] != data['code']:
        return json.dumps({'replay':False,'msg':'کد تایید صحیح نیست'})
    farasahmDb['daraRegister'].insert_one({'phone':phone,'nationalCode':data['nationalCode'],'date':datetime.datetime.now()})
    dic = str({'phone':phone,'nationalCode':data['nationalCode']})
    dic = encrypt(dic).decode()
    return json.dumps({'replay':True,'cookie':dic})

def coderegistered(data):
    registerNoBours = farasahmDb['registerNoBours'].find_one({'کد ملی':data['nationalCode']})
    if registerNoBours != None:
        phone = registerNoBours['شماره تماس']
    else:
        daraRegister = farasahmDb['daraRegister'].find_one({'nationalCode':data['nationalCode']})
        if daraRegister != None:
            phone = daraRegister['phone']

    cheakcode = farasahmDb['VerificationPhone'].find_one({'phone':phone})
    if cheakcode['code'] != data['Code']:
        return json.dumps({'replay':False,'msg':'کد تایید صحیح نیست'})
    dic = str({'phone':phone,'nationalCode':data['nationalCode']})
    dic = encrypt(dic).decode()
    return json.dumps({'replay':True,'cookie':dic})


def checkcookie(data):
    try:
        cookie = data['cookie']
        cookie = literal_eval(decrypt(str(cookie).encode()))
        phone = cookie['phone']
        nationalCode = cookie['nationalCode']
        registerNoBours = farasahmDb['registerNoBours'].find_one({'کد ملی':nationalCode})
        if registerNoBours != None:
            if registerNoBours['شماره تماس'] == phone:
                return json.dumps({'replay':True})
        else:
            daraRegister = farasahmDb['daraRegister'].find_one({'nationalCode':nationalCode})
            if daraRegister['phone'] == phone:
                return json.dumps({'replay':True})
        return json.dumps({'replay':False})
    except:
        return json.dumps({'replay':False})
    
def CookieToUser(cookie):
    try:
        cookie = cookie
        user = literal_eval(decrypt(str(cookie).encode()))
        phone = user['phone']
        nationalCode = user['nationalCode']
        registerNoBours = farasahmDb['registerNoBours'].find_one({'کد ملی':nationalCode})
        if registerNoBours != None:
            if registerNoBours['شماره تماس'] == phone:
                return {'replay':True, 'user':user}
        else:
            daraRegister = farasahmDb['daraRegister'].find_one({'nationalCode':nationalCode})
            if daraRegister['phone'] == phone:
                return {'replay':True,'user':user}
        return {'replay':False}
    except:
        print(0)
        return {'replay':False}
    
def getcompany(data):
    user = CookieToUser(data['cookie'])

    if user['replay']==False: return json.dumps({'replay':False,'msg':'لطفا مجددا وارد شوید'})
    user = user['user']
    stockBourse = pd.DataFrame(farasahmDb['register'].find({'کد ملی':int(user['nationalCode'])},{'_id':0,'symbol':1,'سهام کل':1,'تاریخ گزارش':1}))
    stockBourse = stockBourse.rename(columns={'سهام کل':'تعداد سهام','تاریخ گزارش':'date'})
    listStock = []
    if len(stockBourse)>0:
        for i in list(set(stockBourse['symbol'].to_list())):
            dff = stockBourse[stockBourse['symbol']==i]
            lastDate = dff['date'].max()
            dff = dff[dff['date']==lastDate]
            dff = dff.to_dict('records')[0]
            listStock.append(dff)
    stockNoBourse = pd.DataFrame(farasahmDb['registerNoBours'].find({'کد ملی':str(user['nationalCode'])},{'تعداد سهام':1,'_id':0,'symbol':1,'date':1}))

    if len(stockNoBourse)>0:
        for i in list(set(stockNoBourse['symbol'].to_list())):
            dff = stockNoBourse[stockNoBourse['symbol']==i]
            lastDate = dff['date'].max()
            dff = dff[dff['date']==lastDate]
            dff = dff.to_dict('records')[0]
            listStock.append(dff)
  

    allCompany = pd.DataFrame(farasahmDb['companyList'].find({},{'_id':0}))
    allCompany = allCompany.set_index('symbol')
    listStock = pd.DataFrame(listStock)
    listStock = listStock.set_index('symbol')

    df = allCompany.join(listStock)
    df = df.drop(columns='date')
    df = df.fillna(0)
    df = df.reset_index()
    df = df.to_dict('records')

    return json.dumps({'replay':True,'df':df})


def gettrade(data):
    user = CookieToUser(data['cookie'])
    if user['replay']==False: return json.dumps({'replay':False,'msg':'لطفا مجددا وارد شوید'})
    user = user['user']

    return json.dumps({'reply': True})