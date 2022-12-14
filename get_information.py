'''
数据来源：东方财富网-行情中心
http://quote.eastmoney.com/center
'''
#coding=utf-8
import requests
import re
import pymysql
import pandas as pd
import logging
#import threading
import json
import datetime
import pub_uti_a

logging.basicConfig(level=logging.DEBUG, filename='../log/get_information.log', filemode='w',
                    format='%(asctime)s-%(levelname)5s: %(message)s')


# def get_df_from_db(sql, db):
#     cursor = db.cursor()  # 使用cursor()方法获取用于执行SQL语句的游标
#     cursor.execute(sql)  # 执行SQL语句
#     data = cursor.fetchall()
#     # 下面为将获取的数据转化为dataframe格式
#     columnDes = cursor.description  # 获取连接对象的描述信息
#     columnNames = [columnDes[i][0] for i in range(len(columnDes))]  # 获取列名
#     df = pd.DataFrame([list(i) for i in data], columns=columnNames)  # 得到的data为二维元组，逐行取出，转化为列表，再转化为df
#     cursor.close()
#     return df

'''
【功能】查詢板塊名與板塊編號映射
'''
def get_bk_relation():
    bk_map = {}
    sql = "select distinct bk_name,bk_code from bankuai_day_data"
    res = pub_uti_a.select_from_db(sql)
    for tup in res:
        bk_map[tup[0]] = tup[1]
    return bk_map
def clear_info():
    sql = "delete  from stock_informations"
    pub_uti_a.commit_to_db(sql)
    print('清除成功。')
def get_base_info():
    #清除原数据
    # clear_info()
    bk_map  = get_bk_relation()
    s = pub_uti_a.save()
    count = 1
    for num in range(1,1000):
        num_str = '{:0>3d}'.format(num)
        for capital_num in ['600','601','603','688','002','000','300']:
            if count % 200 == 0:
                s.commit()
                s = pub_uti_a.save()
            stock_id = capital_num + num_str
            sql = get_data(stock_id, bk_map)
            if sql:
                s.add_sql(sql)
                count +=1
                print(num_str,stock_id,'count:',count)
    else:
        s.commit()
def get_data(stock_id,bk_map):
    #基础数据
    if stock_id[0]=='6':
        url = "http://f10.eastmoney.com/CompanySurvey/CompanySurveyAjax?code=SH{}".format(stock_id)
        other_data_url = "http://emweb.securities.eastmoney.com/PC_HSF10/OperationsRequired/PageAjax?code=SH{}".format(stock_id)
    elif stock_id[0]=='0' or stock_id[0]=='3':
        url = "http://f10.eastmoney.com/CompanySurvey/CompanySurveyAjax?code=SZ{}".format(stock_id)
        other_data_url = "http://emweb.securities.eastmoney.com/PC_HSF10/OperationsRequired/PageAjax?code=SZ{}".format(
            stock_id)
    else:
        return None
    header={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'}
    response = requests.get(url,headers=header)
    text=response.text
    # print('text:',text)
    if text.find('股票代码不合法') != -1:
        print('flag')
        return None
    #获取其他数据
    other_data_respone = requests.get(other_data_url,headers=header)
    other_text = other_data_respone.text
    # print('other_text:', other_text)
    try:
        res_json = json.loads(other_text)
    except Exception as err:
        res_json = {}
        logging.error('{} other data respone err:{}'.format(stock_id,other_text))
        print('{} other data respone err:{}'.format(stock_id,other_text))
    zxzb = res_json.get("zxzb",[{}])[0] if len(res_json.get("zxzb",[{}])) else {}
    MGJYXJJE = zxzb.get("MGJYXJJE",0)
    # 流通股数
    FREE_SHARE = zxzb.get("FREE_SHARE",0)
    if not FREE_SHARE:
        FREE_SHARE = 0
        print('FREE_SHARE is None :{}'.format(zxzb))
        logging.warning(('FREE_SHARE is None :{}'.format(zxzb)))
    # 总股数
    TOTAL_SHARE = zxzb.get("TOTAL_SHARE",0)
    if not TOTAL_SHARE:
        TOTAL_SHARE = 0
        print('TOTAL_SHARE is None :{}'.format(zxzb))
        logging.warning(('TOTAL_SHARE is None :{}'.format(zxzb)))
    #现金流
    cash_flow = MGJYXJJE * TOTAL_SHARE
    #总市值
    zxzbOther = res_json.get("zxzbOther", [{}])[0] if len(res_json.get("zxzbOther", [{}])) else {}
    TOTAL_MARKET_CAP = zxzbOther.get("TOTAL_MARKET_CAP",0)
    #避错
    if not TOTAL_MARKET_CAP:
        TOTAL_MARKET_CAP = 0
        print('TOTAL_MARKET_CAP is None :{}'.format(zxzbOther))
        logging.warning(('TOTAL_MARKET_CAP is None :{}'.format(zxzbOther)))
    #流通市值
    free_market= 0
    if FREE_SHARE != 0:
        free_market = TOTAL_MARKET_CAP*(TOTAL_SHARE/FREE_SHARE)
    else:
        print('other 数据为空')
    print()
    zyzb = res_json.get("zyzb", [{}])[0] if len(res_json.get("zyzb", [{}])) else {}
    ZCFZL = zyzb.get("ZCFZL",0)
    print()
    #print('text:',text)
    cym=re.findall('"cym":"(.*?)"',text)[0]
    dchy=re.findall('"sshy":"(.*?)"',text)[0]
    zjhy=re.findall('"sszjhhy":"(.*?)"',text)[0]
    gyrs=re.findall('"gyrs":"(.*?)"',text)[0]
    gsjj = "" #暫時不需要
    #print('gsjj2:',gsjj)
    jyfw=re.findall('"jyfw":"(.*?)"',text)[0]
    jyfw = '' #暫時不需要 需要時需要清洗 \ 符號
    ssrq=re.findall('"ssrq":"(.*?)"',text)[0]
    if ssrq == '--':
        ssrq = '1971-01-01'
    #name
    agjc = re.findall('"agjc":"(.*?)"', text)[0]
    if agjc == '--':
        return None
    fxl=re.findall('"fxl":"(.*?)"',text)[0]
    if  fxl == '--':
        fxl ='0'
    if fxl[-1]=='万':
        fxl = float(fxl[0:-1])*10000
    elif fxl[-1]=='亿':
        fxl = float(fxl[0:-1])*100000000
    else:
        fxl = float(fxl)
    qy=re.findall('"qy":"(.*?)"',text)[0]
    mgfxj=re.findall('"mgfxj":"(.*?)"',text)[0]
    h_table = stock_id[-1]
    #print('cym:',cym,dchy,zjhy,gyrs,gsjj,jyfw,ssrq,'fxl:',fxl,qy)
    bk_code = ''
    if dchy != '--':
        bk_code = bk_map[dchy]
    update_time = datetime.datetime.now().strftime('%Y-%m-%d')
    sql = "insert into stock_informations(stock_id,stock_name,发行量,bk_name,证监会行业," \
          "上市日期,曾用名,每股发行价,区域,雇员人数,经营范围,公司简介,h_table,bk_code,updatetime," \
          "total_market_value,free_market,total_share,free_share,ZCFZL,cash_flow ) " \
          "values ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}','{9}','{10}','{11}','{12}','{13}','{14}'," \
          " '{15}','{16}','{17}','{18}','{19}','{20}') " \
          "ON DUPLICATE KEY UPDATE stock_id='{0}',stock_name='{1}',发行量='{2}',bk_name='{3}'," \
          "证监会行业='{4}',上市日期='{5}',曾用名='{6}',每股发行价='{7}',区域='{8}',雇员人数='{9}',经营范围='{10}'" \
          ",公司简介='{11}',h_table='{12}',bk_code='{13}',updatetime = '{14}',total_market_value='{15}'," \
          "free_market='{16}',total_share='{17}',free_share='{18}',ZCFZL='{19}',cash_flow='{20}' " \
        .format(stock_id,agjc,fxl,dchy,zjhy,ssrq,cym,mgfxj,qy,gyrs,jyfw,gsjj,h_table,bk_code,update_time,
                TOTAL_MARKET_CAP,free_market,TOTAL_SHARE,FREE_SHARE,ZCFZL,cash_flow)
    # sql="update stock_informations set 发行量={0},bk_name='{1}', 证监会行业='{2}', 上市日期='{3}', 曾用名='{4}', 每股发行价='{5}', 区域='{6}', \
    #     雇员人数='{7}', 经营范围='{8}', 公司简介='{9}' where stock_id = '{10}'\
    #     ".format(fxl,dchy,zjhy,ssrq,cym,mgfxj,qy,gyrs,jyfw,gsjj,stock_id)
    # print('sql',sql)
    return sql



def update_other_tab():
    table_list = ['stock_trade_data', ]
    sql = "select stock_name,bk_name,stock_id from stock_informations"
    result = pub_uti_a.select_from_db(sql)
    print('查询完成。',result)
    start_time = datetime.datetime.now()
    s= pub_uti_a.save()
    add_count = 1
    for table in table_list:
        for tup in result:
            sql = "update {0} set stock_name='{1}',bk_name='{2}' where stock_id = '{3}'".format(table,tup[0],tup[1],tup[2])
            print('sql:', add_count,sql)
            s.add_sql(sql)
            add_count += 1
        if add_count%200 == 0:
            s.commit()
            s = pub_uti_a.save()
            print('add_count:',add_count)
    else:
        s.commit()

    print('耗时：{}'.format(datetime.datetime.now() - start_time))
# def update_other_tab(db):
#     table_list = ['stock_trade_data',] #stock_trade_data, monitor
#     sql = "select stock_name,bk_name,stock_id from stock_informations"
#     cursor = db.cursor()
#     cursor.execute(sql)
#     result = cursor.fetchall()
#     print('查询完成。')
#     start_time = datetime.datetime.now()
#     for table in table_list:
#         try:
#             sql = "update {0} set stock_name=(%s),bk_name=(%s) where stock_id = (%s)".format(table)
#             print('sql:',sql)
#             cursor.executemany(sql,result)
#             db.commit()
#             print('储存完成。table:{}'.format(table))
#         except Exception as err:
#             db.rollback()
#             print('存储失败!table:{},{}'.format(table, err))
#             logging.error('存储失败!table:{},{}'.format(table, err))
#     print('耗时：{}'.format(datetime.datetime.now() - start_time))
#     # df = get_df_from_db(sql, db)
#     # cursor = db.cursor()
#     # for i in range(len(df)):
#     #     stock_name = df.loc[i,'stock_name']
#     #     bk_name = df.loc[i,'stock_name']
#     #     stock_id = df.loc[i, 'stock_id']
#     #     print('stock_id:{}'.format(stock_id))
#     #     for tab in table_list:
#     #         sql = "update {0} set stock_name='{1}',bk_name='{2}' where stock_id = '{3}'".format(tab, stock_name,
#     #                                                                                             bk_name,
#     #                                                                                             stock_id)
#     #         cursor.execute(sql)
#     # try:
#     #
#     #     db.commit()
#     #     print('存储完成')
#     # except Exception as err:
#     #     db.rollback()
#     #     print('存储失败:id:{},{}'.format(stock_id, err))
#     #     logging.error('存储失败:id:{},{}'.format(stock_id, err))
#     cursor.close()

#补充缺失数据
def supplement_data():
    #求get_info 与 day_trade 差集合
    trade_sql = "select distinct stock_id from stock_trade_data "
    trade_set = set(pub_uti_a.creat_df(trade_sql)['stock_id'].to_list())
    info_sql = "select stock_id from stock_informations "
    info_set = set(pub_uti_a.creat_df(info_sql)['stock_id'].to_list())
    id_det = trade_set - info_set
    print('id_det:',len(id_det),id_det)
    bk_map  = get_bk_relation()
    s = pub_uti_a.save()
    count = 1
    for stock_id in id_det:
        if count % 200 == 0:
            s.commit()
            s = pub_uti_a.save()
        sql = get_data(stock_id, bk_map)
        if sql:
            s.add_sql(sql)
            count +=1
            print(stock_id,'count:',count)
    else:
        s.commit()
def main(update_flag = 0):
    if update_flag ==1:
        get_base_info()
        update_other_tab()
    elif update_flag == 0:
        get_base_info()
    elif update_flag == 2:
        update_other_tab()


if __name__ == '__main__':
    # main(update_flag = 0)
    supplement_data()
    #test
    # stock_id ='002553'
    # bk_map = get_bk_relation()
    # get_data(stock_id, bk_map)


