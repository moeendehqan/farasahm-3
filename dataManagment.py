
import json
import zipfile
import pandas as pd
from io import StringIO 
from bson import ObjectId

import pymongo
from persiantools.jdatetime import JalaliDate
import datetime
from Login import adminCheck
from sklearn.linear_model import LinearRegression
import re

client = pymongo.MongoClient()
farasahmDb = client['farasahm2']

def zipToDf(zip):
    df = dfDaily = zipfile.ZipFile(zip, 'r')
    df = df.read(df.namelist()[0])
    df = str(df, 'utf-8')
    df = StringIO(df)
    df = pd.read_csv(df, sep='|')
    return df

columnsDaily = ['نماد', 'نماد کدال', 'نام نماد', 'شماره اعلامیه', 'تاریخ معامله','کد خریدار', 'کد سهامداری خریدار تبدیل نشده', 'نام خانوادگی خریدار','نام خریدار', 'سری شناسنامه خریدار', 'سریال شناسنامه خریدار','کد ملی خریدار', 'ش ثبت/ش .شناسنامه خریدار', 'محل صدور خریدار','نام پدر خریدار', 'نوع خریدار', 'نوع سهام خریدار', 'کد فروشنده','کد سهامداری فروشنده تبدیل نشده', 'نام خانوادگی فروشنده', 'نام فروشنده','سری شناسنامه فروشنده', 'سریال شناسنامه فروشنده', 'کد ملی فروشنده','ش ثبت/ش .شناسنامه فروشنده', 'محل صدور فروشنده', 'نام پدر فروشنده','نوع فروشنده', 'نوع سهام فروشنده', 'تعداد سهم', 'قیمت هر سهم','کد کارگزار خریدار', 'نام کارگزار خریدار', 'کد کارگزار فروشنده','نام کارگزار فروشنده']
columnsRegister = ['نماد', 'نماد کدال', 'تاریخ گزارش', 'کد سهامداری','کدسهامداری تبدیل نشده', 'سهام کل', 'سهام سپرده', 'سهام غیرسپرده','نام خانوادگی ', 'نام', 'fullName', 'کد ملی', 'شماره ثبت/شناسنامه',       'تاریخ تولد', 'نام پدر', 'محل صدور', 'سری', 'سریال', 'جنسیت', 'نوع','نوع سهامدار', 'نوع سهام', 'شناسه ملی', 'فرمت قدیم کد سهامداری','سود کدهای وثیقه']

def Update(access,daily,registerdaily):
    dfDaily = zipToDf(daily)
    dfRegister = zipToDf(registerdaily)
    if len(dfDaily)==0: return json.dumps({'replay':False,'msg':'فایل معاملات خالی است'})
    if len(dfRegister)==0: return json.dumps({'replay':False,'msg':'فایل رجیستر خالی است'})
    for i in columnsDaily:
        if i not in dfDaily.columns:return json.dumps({'replay':False,'msg':f'فایل معاملات فاقد ستون {i} است'})
    for i in columnsRegister:
        if i not in dfRegister.columns:return json.dumps({'replay':False,'msg':f'فایل رجیستر فاقد ستون {i} است'})
    dateDaily = list(set(dfDaily['تاریخ معامله']))
    dateregister = list(set(dfRegister['تاریخ گزارش']))
    if dateDaily != dateregister: return json.dumps({'replay':False,'msg':'تاریخ گزارش فایل ها برابر نیست'})
    for i in dateDaily:
        farasahmDb['trade'].delete_many({'تاریخ معامله':i,'symbol':str(access).split(',')[1]})
        farasahmDb['register'].delete_many({'تاریخ گزارش':i,'symbol':str(access).split(',')[1]})
    dfDaily['user'] = str(access).split(',')[0]
    dfRegister['user'] = str(access).split(',')[0]
    dfDaily['symbol'] = str(access).split(',')[1]
    dfRegister['symbol'] = str(access).split(',')[1]
    farasahmDb['trade'].insert_many(dfDaily.to_dict('records'))

    #برای ثبت اخرین ایستگاه های خرید و فروش سهامداران
    dfTradeStation = pd.DataFrame(farasahmDb['trade'].find({'symbol':str(access).split(',')[1]},{'_id':0,'تاریخ معامله':1,'کد خریدار':1,'نام کارگزار خریدار':1,'کد فروشنده':1,'نام کارگزار فروشنده':1}))
    dfTradeStation = dfTradeStation.sort_values('تاریخ معامله',ascending=False)
    dfTradeStationBy = dfTradeStation.copy()[['کد خریدار','نام کارگزار خریدار']]
    dfTradeStationSel = dfTradeStation.copy()[['کد فروشنده','نام کارگزار فروشنده']]
    dfTradeStationBy = dfTradeStationBy.drop_duplicates(subset=['کد خریدار'],keep='first')
    dfTradeStationSel = dfTradeStationSel.drop_duplicates(subset=['کد فروشنده'],keep='first')
    dfTradeStationBy = dfTradeStationBy[dfTradeStationBy['کد خریدار'].isin(dfRegister['کد سهامداری'].to_list())]
    dfTradeStationSel = dfTradeStationSel[dfTradeStationSel['کد فروشنده'].isin(dfRegister['کد سهامداری'].to_list())]
    dfTradeStationBy = dfTradeStationBy.rename(columns={'کد خریدار':'کد سهامداری','نام کارگزار خریدار':'اخرین کارگزاری خرید'})
    dfTradeStationSel = dfTradeStationSel.rename(columns={'کد فروشنده':'کد سهامداری','نام کارگزار فروشنده':'اخرین کارگزاری فروش'})
    dfRegister = dfRegister.set_index('کد سهامداری').join(dfTradeStationBy.set_index('کد سهامداری'),how='left')
    dfRegister = dfRegister.join(dfTradeStationSel.set_index('کد سهامداری'),how='left').reset_index()
    dfRegister['اخرین کارگزاری خرید'] = dfRegister['اخرین کارگزاری خرید'].fillna('ایساتیس پویا')
    dfRegister['اخرین کارگزاری فروش'] = dfRegister['اخرین کارگزاری فروش'].fillna(dfRegister['اخرین کارگزاری خرید'])
    dfRegister = dfRegister.fillna('')
    brokerList = farasahmDb['borkerList'].find({},{'_id':0})
    for brk in brokerList:
        name = list(brk.keys())[0]
        members = brk[name]
        for m in members:
            dfRegister.loc[dfRegister["اخرین کارگزاری خرید"].str.contains(m), "اخرین کارگزاری خرید"] = m
            dfRegister.loc[dfRegister["اخرین کارگزاری فروش"].str.contains(m), "اخرین کارگزاری فروش"] = m


    farasahmDb['register'].insert_many(dfRegister.to_dict('records'))
    return json.dumps({'replay':True,'date':dateDaily})


def createTraders(data):
    symbol = data['access'][1]
    for i in data['date']:
        farasahmDb['traders'].delete_many({'symbol':symbol,'date':i})
        dfTrade = pd.DataFrame(farasahmDb['trade'].find({"تاریخ معامله":i,'symbol':symbol},{'_id':0}))
        dfTrade['Value'] = dfTrade['تعداد سهم'] * dfTrade['قیمت هر سهم']
        dfBuy = dfTrade.groupby('کد خریدار').sum()[['تعداد سهم','Value']].reset_index()
        dfSell = dfTrade.groupby('کد فروشنده').sum()[['تعداد سهم','Value']].reset_index()
        dfBuy.columns = ['کد','تعداد خرید','ارزش خرید']
        dfSell.columns = ['کد','تعداد فروش','ارزش فروش']
        df = pd.concat([dfBuy,dfSell]).fillna(0).groupby('کد').sum()
        dfTrade = dfTrade[['کد خریدار','محل صدور خریدار' ,'محل صدور فروشنده', 'نام خانوادگی خریدار','نام خریدار','کد فروشنده', 'نام خانوادگی فروشنده', 'نام فروشنده','نام کارگزار خریدار','نام کارگزار فروشنده', ]]
        dfBuy = dfTrade[['کد خریدار','محل صدور خریدار' ,'نام خانوادگی خریدار','نام خریدار','نام کارگزار خریدار']]
        dfSell = dfTrade[['کد فروشنده','محل صدور فروشنده','نام خانوادگی فروشنده', 'نام فروشنده','نام کارگزار فروشنده']]
        dfBuy.columns = ['کد','صدور' ,'نام خانوادگی','نام','نام کارگزار']
        dfSell.columns = ['کد','صدور' ,'نام خانوادگی','نام','نام کارگزار']
        dff = pd.concat([dfBuy,dfSell]).fillna('').set_index('کد')
        dff['fullname'] = dff['نام'] +' ' + dff['نام خانوادگی']
        dff = dff.drop(columns=['نام خانوادگی','نام'])
        df = df.join(dff,how='left').reset_index().drop_duplicates(subset=['کد'])
        df['avgBuy'] = df['ارزش خرید'] / df['تعداد خرید']
        df['avgSell'] = df['ارزش فروش'] / df['تعداد فروش']
        register = pd.DataFrame(farasahmDb['register'].find({"تاریخ گزارش":i,'symbol':symbol},{'_id':0,'سهام کل':1,'کد سهامداری':1}))
        register.columns = ['کد', 'سهام کل']
        register = register.drop_duplicates(subset=['کد'])
        register = register.set_index('کد')
        df = df.set_index('کد')
        df = df.join(register,how='left')
        df = df.fillna(0).reset_index()
        df['avgBuy'] = [int(x) for x in df['avgBuy']]
        df['avgSell'] = [int(x) for x in df['avgSell']]
        df = df.drop(columns=['ارزش خرید','ارزش فروش'])
        df['date'] = i
        df['symbol'] = symbol
        farasahmDb['traders'].insert_many(df.to_dict('records'))
    return json.dumps({'replay':True})

def createNewTraders(data):
    symbol = data['access'][1]
    dfTrader = pd.DataFrame(farasahmDb['traders'].find({'symbol':symbol},{'_id':0,'date':1,'سهام کل':1,'تعداد فروش':1,'نام کارگزار':1,'تعداد خرید':1,'کد':1,'fullname':1}))
    for i in data['date']:
        oldLidt = list(set(dfTrader[dfTrader['date']<i]['کد']))
        dfNew = dfTrader[dfTrader['date']==i]
        dfNew = dfNew[dfNew['تعداد خرید']>0]
        dfNew['new'] = dfNew['کد'].isin(oldLidt)
        dic = {'date':i,'allVol':dfNew['تعداد خرید'].sum(),'allCntBuy':len(dfNew)}
        dfNew = dfNew[dfNew['new']==False]
        dic['newVol'] = dfNew['تعداد خرید'].sum()
        dic['newCnt'] = len(dfNew['تعداد خرید'])
        dic['ratNewVol'] = dic['newVol'] / dic['allVol']
        dic['ratNewCnt'] = dic['newCnt'] / dic['allCntBuy']
        dfNew = dfNew[['کد','تعداد خرید','تعداد فروش','نام کارگزار','سهام کل','fullname']]
        dfNew = dfNew.to_dict('records')
        dic['newcomer'] = dfNew
        dic['symbol'] = symbol
        out = pd.DataFrame(farasahmDb['traders'].find({'symbol':symbol,'date':i},{'_id':0,'date':1,'سهام کل':1,'تعداد فروش':1,'نام کارگزار':1,'تعداد خرید':1,'کد':1,'fullname':1}))
        out = out[out['تعداد فروش']>=0]
        dic['allCntSel'] = len(out['تعداد فروش'])
        out = out[out['سهام کل']<=0]
        dic['outVol'] = out['تعداد فروش'].sum()
        dic['outCnt'] = len(out['تعداد فروش'])
        dic['ratOutVol'] = dic['outVol'] / dic['allVol']
        dic['ratOutCnt'] = dic['outCnt'] / dic['allCntSel']
        out = out[['کد','تعداد خرید','تعداد فروش','نام کارگزار','سهام کل','fullname']]
        out = out.to_dict('records')
        dic['runway'] = out
        farasahmDb['newComer'].delete_many({'date':i,'symbol':symbol})
        farasahmDb['newComer'].insert_one(dic)
    return json.dumps({'replay':True})


def createStation(data):
    symbol = data['access'][1]
    for i in data['date']:
        dfTrade = pd.DataFrame(farasahmDb['trade'].find({"تاریخ معامله":i,'symbol':symbol},{'_id':0,'تعداد سهم':1,'قیمت هر سهم':1,'نام کارگزار خریدار':1,'نام کارگزار فروشنده':1}))
        dfTrade['value'] = dfTrade['تعداد سهم'] * dfTrade['قیمت هر سهم']
        dfB = dfTrade[['تعداد سهم','نام کارگزار خریدار','value']]
        dfS = dfTrade[['تعداد سهم','نام کارگزار فروشنده','value']]
        dfB.columns = ['تعداد خرید', 'نام کارگزار', 'ارزش خرید']
        dfS.columns = ['تعداد فروش', 'نام کارگزار', 'ارزش فروش']
        df = pd.concat([dfB,dfS]).groupby('نام کارگزار').sum()
        df['قیمت خرید'] = df['ارزش خرید'] / df['تعداد خرید']
        df['قیمت فروش'] = df['ارزش فروش'] / df['تعداد فروش']
        df = df.reset_index().drop(columns=['ارزش خرید','ارزش فروش']).fillna(0)
        df['قیمت خرید'] = [int(x) for x in df['قیمت خرید']]
        df['قیمت فروش'] = [int(x) for x in df['قیمت فروش']]
        df['date'] = i
        df['symbol'] = symbol
        farasahmDb['station'].delete_many({'symbol':symbol,'date':i})
        farasahmDb['station'].insert_many(df.to_dict('records'))
    return json.dumps({'replay':True})

def createBroker(data):
    symbol = data['access'][1]
    brokerList = [x for x in farasahmDb['borkerList'].find({},{'_id':0})]
    for i in data['date']:
        station = pd.DataFrame(farasahmDb['station'].find({'symbol':symbol,'date':i},{'_id':0}))
        station['broker'] = ''
        station['buyValue'] = station['تعداد خرید'] * station['قیمت خرید']
        station['selValue'] = station['تعداد فروش'] * station['قیمت فروش']
        station = station.drop(columns=['قیمت خرید','قیمت فروش'])
        for s in station.index:
            for b in brokerList:
                name = list(b.keys())[0]
                members = b[name]
                for m in members:
                    if m in station['نام کارگزار'][s]:
                        station['broker'][s] = name
                        break
                        break
        station['broker'] = station['broker'].replace('','نامشخص')
        station = station.groupby('broker').sum().reset_index()
        station['قیمت خرید'] = station['buyValue'] / station['تعداد خرید']
        station['قیمت فروش'] = station['selValue'] / station['تعداد فروش']
        station['قیمت خرید'] = station['قیمت خرید'].fillna(0)
        station['قیمت فروش'] = station['قیمت خرید'].fillna(0)
        station['قیمت خرید'] = [int(x) for x in station['قیمت خرید']]
        station['قیمت فروش'] = [int(x) for x in station['قیمت فروش']]
        station = station.drop(columns=['buyValue','selValue'])
        station['date'] = i
        station['symbol'] = symbol
        farasahmDb['broker'].delete_many({'symbol':symbol,'date':i})
        farasahmDb['broker'].insert_many(station.to_dict('records'))
    return json.dumps({'replay':True})

def createholder(data):
    symbol = data['access'][1]
    dfTrader = pd.DataFrame(farasahmDb['traders'].find({'symbol':symbol},{'_id':0,'date':1,'کد':1}))
    dfRegister = pd.DataFrame(farasahmDb['register'].find({'symbol':symbol},{'_id':0,'تاریخ گزارش':1,'کد سهامداری':1,'fullName':1,'سهام کل':1}))
    for i in data['date']:
        gorgia = JalaliDate(int(str(i)[:4]), int(str(i)[4:6]), int(str(i)[6:])).to_gregorian()
        for j in [3,6,12,18,24]:
            baseGorgia = gorgia - datetime.timedelta(days=j*30)
            basicJalali = int(str(JalaliDate.to_jalali(baseGorgia.year,baseGorgia.month,baseGorgia.day)).replace('-',''))
            active = list(set(dfTrader[dfTrader['date']>=basicJalali]['کد']))
            dfRegisterDisabale = dfRegister[dfRegister['تاریخ گزارش']<basicJalali]
            if len(dfRegisterDisabale)>0:
                dfRegisterDisabale = dfRegisterDisabale[dfRegisterDisabale['تاریخ گزارش']==dfRegisterDisabale['تاریخ گزارش'].max()]
                dfRegisterDisabale['active'] = dfRegisterDisabale['کد سهامداری'].isin(active)
                dfRegisterDisabale = dfRegisterDisabale[dfRegisterDisabale['active']==False]
                if len(dfRegisterDisabale)>0:
                    dfRegisterDisabale = dfRegisterDisabale[['fullName','سهام کل']]
                    dfRegisterDisabale['date'] = i
                    dfRegisterDisabale['period'] = j
                    dfRegisterDisabale['symbol'] = symbol
                    farasahmDb['holder'].delete_many({'symbol':symbol,'period':j,'date':i})
                    farasahmDb['holder'].insert_many(dfRegisterDisabale.to_dict('records'))
    return json.dumps({'replay':True})

def mashinlearninimg(data):
    '''
        ChgRtAvgCntSel50 => changeRate(avg(count(seller),50))
        MnPrc20ToPrc => min(price,20)/price
        AvgPrc50ToPrc => avg(price,50)/price
        ChgStdPrc50 => change(std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50))
        AvgPrc50ToPrc => avg(price,20)/price
        MnMxPrc20ToMacPrc =>min(max(price),20)/max(price)
        MnMnPrc20ToMnPrc => min(min(price),20)/min(price)
        AvgMxPrc20ToMxPrc => avg(max(price),20)/max(price)
        CngMxCntSel5ToMCntSel5 => change(max(count(seller),5)/min(count(seller),5))
        CngAvgCntSel50 => change(avg(count(seller),50))
        CngRtAvgMxPrc20 => changeRate(avg(max(price),20))
    '''
    # trade => date, volume, value saller price
    # newComer => date, allCntSel



    symbol = data['access'][1]
    for i in data['date']:
        df = pd.DataFrame(farasahmDb['trade'].find({'symbol':symbol},{'_id':0,'تاریخ معامله':1,'تعداد سهم':1,'قیمت هر سهم':1}))
        df.columns = ['date', 'volume', 'price']
        df = df[df['date']<=i]

        # در اینجا ما حداکثر به 50 روز کار اخیر نیاز داریم که اینجوری مابقی روز ها رو حذف کردیم
        lastDate50 = sorted(list(set(df['date'])),reverse=True)[:50]
        df = df[df['date']>=min(lastDate50)]
        
        df['value'] = df['volume'] * df['price']

        minDf = df.groupby('date').min()[['price']]
        minDf.columns = ['min(price)']
        maxDf = df.groupby('date').max()
        maxDf.columns = ['max(volume)','max(price)','max(value)']
        avgDf = df.groupby('date').mean()
        avgDf.columns = ['avg(volume)','avg(price)','avg(value)']
        df = df.groupby('date').sum()
        sallerDf = pd.DataFrame(farasahmDb['newComer'].find({'symbol':symbol},{'_id':0,'date':1,'allCntSel':1,'newCnt':1}))
        sallerDf =sallerDf[sallerDf['date']<=i]
        sallerDf =sallerDf[sallerDf['date']>=min(lastDate50)]
        sallerDf.columns = ['date','countNewBuyer','count(seller)']
        df = df.join(minDf).join(maxDf).join(avgDf).join(sallerDf.set_index('date'))
        # create => (max(price)-min(price))/avg(price) , price
        df['(max(price)-min(price))/avg(price)'] = (df['max(price)'] - df['min(price)']) / df['avg(price)']
        df['price'] = df['value'] / df['volume']
        df = df.sort_index()
        # avg : 50 => [count(seller) , price, (max(price)-min(price))/avg(price)]  20 => [price , max(price)]
        df['avg(count(seller),50)'] = df['count(seller)'].rolling(window=50,min_periods=1).mean()
        df['avg(price,50)'] = df['price'].rolling(window=50,min_periods=1).mean()
        df['avg(price,20)'] = df['price'].rolling(window=20,min_periods=1).mean()
        df['avg((max(price)-min(price))/avg(price),50)'] = df['(max(price)-min(price))/avg(price)'].rolling(window=50,min_periods=1).mean()
        df['avg(max(price),20)'] = df['max(price)'].rolling(window=20,min_periods=1).mean()
        # std : 50 => [(max(price)-min(price))/avg(price)]
        df['std((max(price)-min(price))/avg(price),50)'] = df['(max(price)-min(price))/avg(price)'].rolling(window=50,min_periods=1).std()
        # min : 20 => [price, max(price) , min(price)] 5 => [count(seller)]
        df['min(price,20)'] = df['price'].rolling(window=20,min_periods=1).min()
        df['min(max(price),20)'] = df['max(price)'].rolling(window=20,min_periods=1).min()
        df['min(min(price),20)'] = df['min(price)'].rolling(window=20,min_periods=1).min()
        df['min(count(seller),5)'] = df['count(seller)'].rolling(window=5,min_periods=1).min()
        # max : 5 => [count(seller)]
        df['max(count(seller),5)'] = df['count(seller)'].rolling(window=5,min_periods=1).max()
        # create => std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50), avg(max(price),20)/max(price)
        df['std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50)'] = df['std((max(price)-min(price))/avg(price),50)'] / df['avg((max(price)-min(price))/avg(price),50)']
        df['avg(max(price),20)/max(price)'] = df['avg(max(price),20)'] / df['max(price)']
        # create => max(count(seller),5)/min(count(seller),5)
        df['max(count(seller),5)/min(count(seller),5)'] = df['max(count(seller),5)'] / df['min(count(seller),5)']

        # changeRate => [avg(count(seller),50),avg(max(price),20)]
        df['changeRate(avg(count(seller),50))'] = (df['avg(count(seller),50)'].shift(-1) / df['avg(count(seller),50)']).fillna(0)
        df['changeRate(avg(max(price),20))'] = (df['avg(max(price),20)'].shift(-1) / df['avg(max(price),20)']).fillna(0)
        # change => [std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50), avg(max(price),20)/max(price), max(count(seller),5)/min(count(seller),5), avg(count(seller),50)]
        df['change(std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50))'] = (df['std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50)'].shift(-1) - df['std((max(price)-min(price))/avg(price),50)/avg((max(price)-min(price))/avg(price),50)']).fillna(0)
        df['change(max(count(seller),5)/min(count(seller),5))'] = (df['max(count(seller),5)/min(count(seller),5)'].shift(-1) - df['max(count(seller),5)/min(count(seller),5)']).fillna(0)
        df['change(avg(count(seller),50))'] = (df['avg(count(seller),50)'].shift(-1) - df['avg(count(seller),50)']).fillna(0)
        # create => min(price,20)/price , avg(price,50)/price , avg(price,20)/price , min(max(price),20)/max(price), min(min(price),20)/min(price)
        df['min(price,20)/price'] = df['min(price,20)'] / df['price']
        df['avg(price,50)/price'] = df['avg(price,50)'] / df['price']
        df['avg(price,20)/price'] = df['avg(price,20)'] / df['price']
        df['min(max(price),20)/max(price)'] = df['min(max(price),20)'] / df['max(price)']
        df['min(min(price),20)/min(price)'] = df['min(min(price),20)'] / df['min(price)']
        # create => avg(max(price),20)/max(price)
        df['avg(max(price),20)/max(price)'] = df['avg(max(price),20)'] / df['max(price)']
        df = df.fillna(df.mean())
        df = df[df.index==df.index.max()].reset_index()
        df = df.to_dict('records')[0]
        df['symbol'] = symbol
        # insert Db
        farasahmDb['features'].delete_many({'symbol':symbol,'date':i})
        farasahmDb['features'].insert_one(df)
        # predict
        df = pd.DataFrame(farasahmDb['features'].find({'symbol':symbol},{'_id':0,'predict_CountNewBuyer':0}))
        df = df[df['date']<=i]
        # برای پیشبینی حداقل نیاز به 50 روز سابقه معاملاتی است
        if len(df)<=50:return json.dumps({'replay':True})
        modelRegression = LinearRegression()
        # predict newComer
        df['countNewBuyer'] = df['countNewBuyer'].shift(-1)
        dftrain = df[df['date']<i]
        dftest = df[df['date']==i]
        x_train = dftrain[['changeRate(avg(count(seller),50))','min(price,20)/price','avg(price,20)/price','avg(price,50)/price']]
        y_train = dftrain[['countNewBuyer']]
        x_test = dftest[['changeRate(avg(count(seller),50))','min(price,20)/price','avg(price,20)/price','avg(price,50)/price']]
        modelRegression.fit(x_train, y_train)
        y_pred = modelRegression.predict(x_test)[0][0]

        farasahmDb['features'].update_one({'symbol':symbol,'date':i},{'$set':{'predict_CountNewBuyer':y_pred}})
    return json.dumps({'replay':True})

def lastupdate(data):
    symbol = data['access'][1]
    #result = farasahmDb['trade'].find_one({'symbol':symbol},sort=[("تاریخ معامله", pymongo.DESCENDING)])
    resultList = farasahmDb['trade'].find({'symbol':symbol},{"تاریخ معامله":1})

    resultList =[x['تاریخ معامله'] for x in resultList]

    if len(resultList) == 0: result = '-'
    else:
        result = max(resultList)
        resultInt = int(result)
        resultstr = str(result)
        resultslash = resultstr[:4]+'/'+resultstr[4:6]+'/'+resultstr[6:]
        gorgia = str(JalaliDate(int(str(resultstr)[:4]), int(str(resultstr)[4:6]), int(str(resultstr)[6:])).to_gregorian())
        resultList = [str(x) for x in resultList]
    return json.dumps({'replay':True,'resultslash':resultslash,'resultInt':resultInt,'gorgia':gorgia,'resultList':resultList})



def setgrouping(data):
    dic = {'symbol':data['access'][1], 'nameGroup':data['name'], 'members':[x['کد'] for x in data['members']], 'user':data['access'][0]}
    if farasahmDb['grouping'].find_one({'nameGroup':dic['nameGroup'],'symbol':data['access'][1]}) != None:
        farasahmDb['grouping'].delete_many({'nameGroup':dic['nameGroup']})
    allgroup = farasahmDb['grouping'].find({'symbol':data['access'][1]})
    allgroup = [x['members'] for x in allgroup]
    allgroupMarge = []
    for i in allgroup:
        allgroupMarge = allgroupMarge + i
    for i in dic['members']:
        if i in allgroupMarge:
            return json.dumps({'replay':False, 'msg':f'کد {i} قبلا در یک گروه قرار گرفته است'})
    farasahmDb['grouping'].insert_one(dic)
    return json.dumps({'replay':True})

def delrowgrouping(data):
    farasahmDb['grouping'].delete_many({'nameGroup':data['ditail']['name'],'symbol':data['access'][1]})
    return json.dumps({'replay':True})

def setTransaction(data):
    symbol = data['access'][1]
    data['dataTrade']['volume'] = int(data['dataTrade']['volume'])
    data['dataTrade']['price'] = int(data['dataTrade']['price'])
    data['dataTrade']['value'] = int(data['dataTrade']['value'])
    data['dataTrade']['symbol'] = symbol
    Tansaction = farasahmDb['transactions'].find_one({'symbol':symbol,'id':int(data['dataTrade']['id'])})
    if Tansaction == None:
        dfRegister = pd.DataFrame(farasahmDb['registerNoBours'].find({'symbol':symbol},{'_id':0}))
        lastDate = dfRegister['date'].max()
        toDay = int(str(JalaliDate.today()).replace('-',''))
        dfRegister = dfRegister[dfRegister['date']==lastDate]

        dfRegister = dfRegister.set_index('نام و نام خانوادگی')
        balanceSaller = dfRegister['تعداد سهام'][data['dataTrade']['sell']] - int(data['dataTrade']['volume'])
        balanceBuyer = dfRegister['تعداد سهام'][data['dataTrade']['buy']] + int(data['dataTrade']['volume'])
        if balanceSaller<0:return json.dumps({'replay':False,'msg':'مانده فروشنده کافی نمیباشد'})
        dfRegister['تعداد سهام'][data['dataTrade']['sell']] = balanceSaller
        dfRegister['تعداد سهام'][data['dataTrade']['buy']] = balanceBuyer
        dfRegister['date'] = toDay
        dfRegister = dfRegister.reset_index()
        data['dataTrade']['date'] = toDay
        farasahmDb['registerNoBours'].delete_many({'symbol':symbol,'date':toDay})
        farasahmDb['registerNoBours'].insert_many(dfRegister.to_dict('records'))
        farasahmDb['transactions'].insert_one(data['dataTrade'])
        return json.dumps({'replay':True})
    else:
        dfRegister = pd.DataFrame(farasahmDb['registerNoBours'].find({'symbol':symbol},{'_id':0}))
        Date = Tansaction['date']
        dfRegister = dfRegister[dfRegister['date']>=Date]
        dfRegister = dfRegister.set_index('نام و نام خانوادگی')
        newVol = data['dataTrade']['volume'] - Tansaction['volume']
        DateList = list(set(dfRegister['date'].to_list()))
        for d in DateList:
            dfRegisterD = dfRegister[dfRegister['date']==d]
            balanceSaller = dfRegisterD['تعداد سهام'][data['dataTrade']['sell']] - newVol
            balanceBuyer = dfRegisterD['تعداد سهام'][data['dataTrade']['buy']] + newVol
            if balanceSaller<0 or balanceBuyer<0: return json.dumps({'replay':False,'msg':'ویرایش قابل اجرا نیست'})
            dfRegisterD['تعداد سهام'][data['dataTrade']['sell']] = balanceSaller
            dfRegisterD['تعداد سهام'][data['dataTrade']['buy']] = balanceBuyer
            dfRegister = dfRegister[dfRegister['date']!=d]
            dfRegister = pd.concat([dfRegister,dfRegisterD])
        for d in DateList:
            farasahmDb['registerNoBours'].delete_many({'symbol':symbol,'date':d})
        dfRegister = dfRegister.reset_index()
        dfRegister = dfRegister.to_dict('records')
        farasahmDb['registerNoBours'].insert_many(dfRegister)
        farasahmDb['transactions'].delete_many({'symbol':symbol,'id':int(data['dataTrade']['id'])})
        data['dataTrade']['date'] = Tansaction['date']
        farasahmDb['transactions'].insert_one(data['dataTrade'])
        return json.dumps({'replay':True})


def deltransaction(data):
    symbol = data['access'][1]
    dfRegister = pd.DataFrame(farasahmDb['registerNoBours'].find({'symbol':symbol},{'_id':0}))
    Date = data['transaction']['date']
    dfRegister = dfRegister[dfRegister['date']>=Date]
    dfRegister = dfRegister.set_index('نام و نام خانوادگی')
    DateList = list(set(dfRegister['date'].to_list()))
    for d in DateList:
        dfRegisterD = dfRegister[dfRegister['date']==d]
        balanceSaller = dfRegisterD['تعداد سهام'][data['transaction']['sell']] + data['transaction']['volume']
        balanceBuyer = dfRegisterD['تعداد سهام'][data['transaction']['buy']] - data['transaction']['volume']
        if balanceSaller<0 or balanceBuyer<0: return json.dumps({'replay':False,'msg':'حذف قابل اجرا نیست'})
        dfRegisterD['تعداد سهام'][data['transaction']['sell']] = balanceSaller
        dfRegisterD['تعداد سهام'][data['transaction']['buy']] = balanceBuyer
        dfRegister = dfRegister[dfRegister['date']!=d]
        dfRegister = pd.concat([dfRegister,dfRegisterD])
    for d in DateList:
        farasahmDb['registerNoBours'].delete_many({'symbol':symbol,'date':d})
    dfRegister = dfRegister.reset_index()
    dfRegister = dfRegister.to_dict('records')
    farasahmDb['registerNoBours'].insert_many(dfRegister)
    farasahmDb['transactions'].delete_many({'symbol':symbol,'id':int(data['transaction']['id'])})
    return json.dumps({'replay':True})


def addtradernobourse(data):
    symbol = data['access'][1]
    if '_id' in data['dataTrader']:
        del data['dataTrader']['_id']
        farasahmDb['registerNoBours'].update_many({'symbol':symbol,'نام و نام خانوادگی':data['dataTrader']['نام و نام خانوادگی']},{'$set':data['dataTrader']})
    else:
        check = farasahmDb['registerNoBours'].find_one({'symbol':symbol,'نام و نام خانوادگی':data['dataTrader']['نام و نام خانوادگی']})!=None
        if check:return json.dumps({'replay':False,'msg':'سهامداری با همین نام موجود است امکان ثبت وجود ندارد'})
        check = farasahmDb['registerNoBours'].find_one({'symbol':symbol,'کد ملی':data['dataTrader']['کد ملی']})!=None
        if check:
            farasahmDb['registerNoBours'].delete_many({'symbol':symbol,'کد ملی':data['dataTrader']['کد ملی']})
        lastDate = farasahmDb['registerNoBours'].find_one({'symbol':symbol},sort=[("date", pymongo.DESCENDING)])['date']
        dic = data['dataTrader']
        dic['symbol'] = symbol
        dic['date'] = lastDate
        dic['تعداد سهام'] = 0
        farasahmDb['registerNoBours'].insert_one(dic)
    return json.dumps({'replay':True})



def delshareholders(data):
    symbol = data['access'][1]
    name = data['transaction']['نام و نام خانوادگی']
    check = pd.DataFrame(farasahmDb['registerNoBours'].find({'symbol':symbol,'نام و نام خانوادگی':name}))
    if check['تعداد سهام'].max()>0: return json.dumps({'replay':False,'msg':f'"{name}" قابل حذف نیست'})
    trnc = farasahmDb['transactions'].find_one({'symbol':symbol,'sell':name})!=None
    if trnc: return json.dumps({'replay':False,'msg':f'"{name}" قابل حذف نیست'})
    trnc = farasahmDb['transactions'].find_one({'symbol':symbol,'buy':name})!=None
    if trnc: return json.dumps({'replay':False,'msg':f'"{name}" قابل حذف نیست'})
    farasahmDb['registerNoBours'].delete_many({'symbol':symbol,'نام و نام خانوادگی':name})
    return json.dumps({'replay':True})

def setinformationcompany(data):
    print(data)
    symbol = data['access'][1]
    dic = data['information']
    dic['symbol'] = symbol
    print(dic)
    farasahmDb['companyBasicInformation'].delete_many({'symbol':symbol})
    farasahmDb['companyBasicInformation'].insert_one(dic)
    return json.dumps({'replay':True})

def syncBoursi(data):
    admin = adminCheck(data['id'])
    if admin:
        df = list(set(pd.DataFrame(farasahmDb['registerNoBours'].find())['کد ملی'].to_list()))
        for i in df:
            newData = farasahmDb['register'].find_one({'شناسه ملی':int(i)})
            if newData != None:
                farasahmDb['registerNoBours'].update_many({'کد ملی':i},{'$set':{'تاریخ تولد':newData['تاریخ تولد'],'کدبورسی':newData['کد سهامداری'],'صادره':newData['محل صدور'],'نام پدر':newData['نام پدر']}})
    return json.dumps({'replay':True})


def syncbook(data):
    admin = adminCheck(data['id'])
    if admin:
        df = pd.DataFrame(farasahmDb['registerNoBours'].find())
        symbols = list(set(df['symbol']))
    return json.dumps({'replay':True})

def createassembly(data):
    symbol = data['access'][1]
    date = data['date']/1000
    date = datetime.datetime.fromtimestamp(date)
    if date<= datetime.datetime.now():
        return json.dumps({'replay':False, 'msg': 'تاریخ نمیتواند ماقبل اکنون باشد'})
    dic = data['dict']
    dic['symbol'] = symbol
    dic['date'] = date
    farasahmDb['assembly'].insert_one(dic)
    return json.dumps({'replay':True})


def delassembly(data):
    symbol = data['access'][1]
    assembly = data['idassembly']
    farasahmDb['assembly'].delete_one({'_id':ObjectId(data['_id'])})
    return json.dumps({'replay':True})

