import flask
import gspread
import keygenerator
from Form_model import SignupForm
import postgres
import random
import time
from datetime import datetime
api= flask.Blueprint('api', __name__,template_folder='../Templates',static_folder='../Static')
gc = gspread.service_account_from_dict(keygenerator.get_db_auth())

@api.route('/verify_usr/',methods=['POST'])
def verify_user():
    if 'id' in flask.session:
        return flask.jsonify({'msg':'User Already Logged In','id':flask.session['ID']}),200
    else:
        if 'email' in flask.request.get_json() and 'pass' in flask.request.get_json():
            data=flask.request.get_json()
            postgres_find_query="""
            with coins as (SELECT c.clientid, sum(c.coin_in::INTEGER)-sum(c.coin_out::INTEGER) as coin from clients.coin_history c
            GROUP by c.clientid)
            SELECT d.clientid,d.email_id,d.cl_password,d.client_name,co.coin from clients.details as d
            LEFT JOIN coins co on d.clientid = co.clientid
            Where lower(d.email_id) like '{0}'
            LIMIT 1;
            """.format(data['email'])
            #print(postgres_find_query)
            res,err=postgres.postgres_connect(postgres_find_query,commit=0)
            details=[list(e) for e in res]
            if len(details)>0 and len(err)==0:
                    if data['pass'] == details[0][2]:
                            flask.session['id']=details[0][0]
                            return flask.jsonify({'msg':'Logged in Successfully as : '+details[0][3],'id':flask.session['id']}),200
                    else:
                            return flask.jsonify({'msg':'Password Incorrect'}),400
            else:
                    return flask.jsonify({'msg':'Please Register First'}),400
        else:
            return flask.jsonify({'msg':"error"}),400

@api.route('/Generate_Random_test/',methods=['POST'])
def Generate_Random_test():
    if 'id' in flask.request.get_json() and 'order_id' in flask.request.get_json():
        data=flask.request.get_json()
        sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1vYStVgetyDmsbZ-AXfiSvTRXwpTxsLaH4FFa1weFZ-I/edit?usp=sharing')
        wks=sh.worksheet("Question_Details")
        IDs= random.sample(range(2, 30), int(data['length']))
        Questions=[]
        answers=[]
        Questionids=[]
        for i in range(len(IDs)):
            row =wks.row_values(IDs[i])
            time.sleep(random.randint(0,4))
            Questions.append([i+1,row[7],row[8],row[9],row[10],row[11]])
            answers.append([i+1,row[12]])
            Questionids.append([i+1,row[0]])
        postgres_insert_query = """
                                            INSERT INTO ecommerce.generated_tests(client_id,order_id,questions,Generation_ts)
                                            VALUES ('{0}','{1}','{2}',CURRENT_TIMESTAMP)
                                            """.format(data['id'],data['order_id'],'|'.join([str(x[1]) for x in Questionids]))
        # print('|'.join([str(x[1]) for x in Questionids]))
        a=postgres.postgres_connect(postgres_insert_query,commit=1)
        return flask.jsonify({'Questions':Questions,'Answers':answers,'QuestionID':Questionids}),200
    else:
        return flask.jsonify({'msg':'You Do not have the access to view this'}),400
    
@api.route('/purchase_through_coins/',methods=['POST'])
def purchase_through_coins():
    """Rqruires : Id,email,Price,Product_id,"""
    if 'id' in flask.request.get_json():
        data=flask.request.get_json()
        postgres_find_query="""
            SELECT c.clientid, sum(c.coin_in::INTEGER)-sum(c.coin_out::INTEGER) as coin from clients.coin_history c
            Where c.clientid like '{0}'
            group by c.clientid
            LIMIT 1;
            """.format(data['id'])
            #print(postgres_find_query)
        res,err=postgres.postgres_connect(postgres_find_query,commit=0)
        details=[list(e) for e in res]
        if len(details)>0:
            details=details[0]
            print(details)
            if details[1]<int(data['price']):
                return flask.jsonify({'msg':'Not Enough Coins'}),400 
            else:
                otp=random.randint(100000,999999)
                od_token=data['id']+'-COINS-'+data['price']+'-'+datetime.now().strftime("%d%m%Y%H%M%S")+'-'+str(otp)
                postgres_insert_query="""INSERT INTO ecommerce.orders
                (email,product_id,coupon_id,order_total,order_disc,final_price,order_ts,client_id,od_token,comodity_id,complition_otp)
                VALUES ('{0}','{1}','COINS-{2}-{3}','{4}','{4}','0',CURRENT_TIMESTAMP,'{2}','{7}','{5}','{6}')
                """.format(data['email'],data['product_id'],data['id'],data['price'],int(data['price'])*.05,data['como_id'],otp,od_token)
                a=postgres.postgres_connect(postgres_insert_query,commit=1)
                # print(postgres_insert_query)
                postgres_insert_query = """INSERT INTO clients.coin_history(clientid,comodityid,coin_in,coin_out,transaction_time)
                                            VALUES ('{0}','{1}',{2},{3},CURRENT_TIMESTAMP)""".format(data['id'],data['product_id'],0,data['price'])
                a=postgres.postgres_connect(postgres_insert_query,commit=1)
                # print(postgres_insert_query)
                return flask.jsonify({'msg':'Success','od_token':od_token,'otp':otp}),200
        else:
            return flask.jsonify({'msg':'Please Logout and Login Again'}),400

@api.route('/purchase_through_coupons/',methods=['POST'])
def purchase_through_coupons():
    """Rqruires : Id,email,Price,Product_id,Coupon_id"""
    if 'id' in flask.request.get_json():
        data=flask.request.get_json()
        otp=random.randint(100000,999999)
        od_token=data['id']+'-COUPONS-'+data['price']+'-'+datetime.now().strftime("%d%m%Y%H%M%S")+'-'+str(otp)
        postgres_insert_query="""INSERT INTO ecommerce.orders
        (email,product_id,coupon_id,order_total,order_disc,final_price,order_ts,client_id,od_token,comodity_id,complition_otp)
        VALUES ('{0}','{1}','{3}','{4}','{4}','0',CURRENT_TIMESTAMP,'{2}','{7}','{5}','{6}')
        """.format(data['email'],data['product_id'],data['id'],data['coupon'],int(data['price']),data['como_id'],otp,od_token)
        a=postgres.postgres_connect(postgres_insert_query,commit=1)
        # print(postgres_insert_query)
        postgres_update_query="""UPDATE ecommerce.coupons 
                                    SET expired = '1'
                                    WHERE coupon_code = '{0}'""".format(data['coupon'])
        a=postgres.postgres_connect(postgres_update_query,commit=1)
        if int(data['product_id']) in (6,7,8,9):
            postgres_insert_query = """INSERT INTO clients.coin_history(clientid,comodityid,coin_in,coin_out,transaction_time)
                                        VALUES ('{0}','{1}',{2},{3},CURRENT_TIMESTAMP)""".format(data['id'],data['product_id'],int(data['price'])*20,0)
            a=postgres.postgres_connect(postgres_insert_query,commit=1)
        # print(postgres_insert_query)
        return flask.jsonify({'msg':'Success','od_token':od_token,'otp':otp}),200
    else:
        return flask.jsonify({'msg':'Please Logout and Login Again'}),400





