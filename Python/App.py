from flask import Flask, render_template, request, redirect, send_file, send_from_directory, url_for, session, g
from pymysql.constants import CLIENT
import pymysql.cursors
import datetime
import os
from datetime import datetime as dt
from package import unzipfile
import logging
from flask_wtf.csrf import CSRFProtect

logging.basicConfig(filename='app.log', filemode='w')

# Sameer: Code start
UPLOAD_FOLDER = '/var/www/html/rtgshop/static/uploads/'
USERDATA_FOLDER = '/var/www/html/rtgshop/static/UserData/'
ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg', 'zip' }

# Sameer: Code end
def get_file_ext(filename):
    ext = filename.rsplit('.')
    return ext[len(ext)-1]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# Sameer: Code end

# Do hard refresh on web page if something does not loading
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['USERDATA_FOLDER'] = USERDATA_FOLDER

csrf = CSRFProtect(app)


# Variables (make global in method if you are writing to it)
employee = False
loggedinid = None
loggedinname = None
lastorderid = None

@app.route("/")
def home():
    global loggedinid, loggedinname, lastorderid,employee
    if 'logoff' in request.args:
        loggedinid = None
        loggedinname = None
        lastorderid = None
        session.clear()
    return render_template('index.html', employee=employee, loggedin=loggedinname, title='Home', styles='album.css', bodyclass='bg-light')


@app.before_request
def before_request():
    g.user = None
    global loggedinid, loggedinname, lastorderid, employee
    if "user" in session:
        g.user = session["user"]
        loggedinid = g.user["loggedinid"]
        loggedinname = g.user["loggedinname"]
        employee = g.user["employee"]
    else:
        employee = False
        loggedinid = None
        loggedinname = None
        lastorderid = None
 

@app.route("/signup.html", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        table = getPersonTable()
        idn = len(table) + 1
        name = request.form['firstName'] + ' ' + request.form['lastName']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        bday = request.form['birthday']

        insertPerson(idn, email, name, datetime.datetime.strptime(bday, '%m/%d/%Y'), phone, dt.today().strftime('%Y-%m-%d'), 'N')
        insertCustomer(idn, password, 'N')
        return redirect('/signin.html')
    return render_template('signup.html', title='Sign Up', styles='signin.css', bodyclass='text-center')
csrf.exempt
@app.route("/delete_user")
def delete_user():
    idn = request.args.get('idn')
    print(idn)
    deleteFromCustomer(idn)
    deleteFromPerson(idn)
    return redirect('/signin.html')


@app.route("/signin.html", methods=['GET', 'POST'])
def login():
    global loggedinid, loggedinname, employee
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            # Check if customer
            cursor = client.cursor()
            # query = "SELECT P.Email, C.CustomerID, C.Userpass, P.Named FROM Customer C, Person P " \
            #         "WHERE C.CustomerID = P.ID"

            # Binary SQL Injection attack on login. Use a valid user email and password=1' OR '1=1
            cursor.execute("SELECT P.Email, C.CustomerID, C.Userpass, P.Named FROM Customer C, Person P " \
                    "WHERE C.CustomerID = P.ID AND C.Userpass='%s'"% (password))
            # Defense mechanism: Using of parameterized queries to sanitize the input paramater
            # Parameterized query of the previous query
            # cursor.execute("SELECT P.Email, C.CustomerID, C.Userpass, P.Named FROM Customer C, Person P " \
            #                "WHERE C.CustomerID = P.ID AND C.Userpass=%s", (password))
            results = cursor.fetchall()
            for customer in results:
                if customer[0] == email:
                    loggedinid = customer[1]
                    loggedinname = customer[3]
                    employee = False
                    user = {"loggedinid": loggedinid, "loggedinname": loggedinname, "employee": employee}
                    session["user"] = user
                    break
            if loggedinid != None:
                return redirect('/')
            else:
                # Check if employee
                query = "SELECT E.EmployeeEmail, E.Userpass, P.Named FROM Employee E, Person P WHERE E.ID = P.ID"
                cursor.execute(query)
                results = cursor.fetchall()
                for employee in results:
                    if employee[0] == email and employee[1] == password:
                        loggedinid = employee[0]
                        loggedinname = employee[2]
                        employee = True
                        user = {"loggedinid": loggedinid, "loggedinname": loggedinname, "employee": employee}
                        session["user"] = user
                        break
            if loggedinid != None:
                return redirect('/')
        except Exception:
            logging.error("Can not retrieve specified Customer/Employee Entity")
        finally:
            client.close()
    return render_template('signin.html', employee=employee, title='Log In', styles='signin.css', bodyclass='text-center')


@app.route("/checkout.html", methods=['GET', 'POST'])
def checkout():
    global loggedinid, lastorderid, employee
    ordersuccessful = False
    items = None
    cards = None
    addresses = None
    quantity = 0
    total = 0
    discount = 0
    shipment = 5
    addbtn = True
    cardValue = [None, None, None, None]
    addressValue = [None, None, None, None, None]

    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        # For things on the right side of the checkout page
        cursor = client.cursor()
        query = "SELECT I.ItemType, S.Quantity, I.ItemDesc, I.Price, S.ItemID, I.Quantity " \
                "FROM Item I, ShoppingCart S WHERE S.CustomerID = %s AND I.ItemID = S.ItemID"
        cursor.execute(query, loggedinid)
        items = cursor.fetchall()

        hasmembership = 'Y'
        query = "SELECT HasMembership FROM Customer WHERE CustomerID = %s AND HasMembership = %s"
        cursor.execute(query, (loggedinid, hasmembership))
        currentcust = cursor.fetchall()

        # Get discounts and no shipping fee if member
        ismember = False
        for row in currentcust:
            ismember = True

        if ismember:
            valid = 'Y'
            query = "SELECT DiscountPercent FROM Discount WHERE Valid = %s"
            cursor.execute(query, valid)
            discountvalues = cursor.fetchall()
            for row in discountvalues:
                discount += row[0]
            shipment = 0

        # Get sum of prices
        for row in items:
            total += row[1] * row[3]
            quantity += row[1]

        total -= (total * discount)
        total += shipment

        # Get customer cards
        query = "SELECT CustomerID, CardName, CardNum, CardComp, CardExp FROM Cards WHERE CustomerID = %s"
        cursor.execute(query, loggedinid)
        cards = cursor.fetchall()

        # Get customer addresses
        query = "SELECT CustomerID, Address1, Address2, State, Country, Zip FROM Addresses WHERE CustomerID = %s"
        cursor.execute(query, loggedinid)
        addresses = cursor.fetchall()
    except Exception:
        logging.error('Could not get shopping cart and/or address/cards data')
    finally:
        client.close()

    if request.method == 'POST':
        if 'checkout' in request.form:
            name = request.form['firstName'] + ' ' + request.form['secondName']
            email = request.form['email']
            billaddress1 = request.form['address']
            billaddress2 = request.form['address2']
            billstate = request.form['state']
            billcountry = request.form['country']
            billzip = request.form['zip']
            cardName = request.form['cardName']
            cardNum = request.form['cardNum']
            cardExp = request.form['expiration']
            cardCVV = request.form['cardCVV']
            cardType = request.form['cardType']
            shipname = request.form['firstNameShip'] + ' ' + request.form['secondNameShip']
            shipaddress1 = request.form['addressShip']
            shipaddress2 = request.form['address2Ship']
            shipstate = request.form['stateShip']
            shipcountry = request.form['countryShip']
            shipzip = request.form['zipShip']

            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "SELECT CustomerID, ItemID, Quantity FROM ShoppingCart WHERE CustomerID = %s"
                cursor.execute(query, loggedinid)
                results = cursor.fetchall()

                # Create Orders Entity
                table = getOrdersTable()
                orderid = len(table) + 1
                query = "INSERT INTO Orders(OrderNum, CustomerID, OrderDate, Completed, OrderName, OrderEmail) \
                                values(%s, %s, %s, %s, %s, %s)"
                cursor.execute(query, (orderid, loggedinid, dt.today().strftime('%Y-%m-%d'), 'N', name, email))  # MAKE PENDING PAGE FOR ORDERS

                # Create Shipment Entity
                customer = getCustomerTuple(loggedinid)
                fee = '5'
                for row in customer:
                    if row[2] == 'Y':
                        fee = '0'
                query = "INSERT INTO Shipment(OrderID, Address1, Address2, State, Country, Zip, Fee, Company, ShipName) values(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(query, (orderid, shipaddress1, shipaddress2, shipstate, shipcountry, shipzip, fee, 'UPS', shipname))

                # Create Payment Entity
                query = "INSERT INTO Payment(OrderID, CardName, CardNum, CardComp, CardExp, Address1, Address2, State, Country, Zip) \
                        values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(query, (orderid, cardName, cardNum, cardType, datetime.datetime.strptime('01' + cardExp, '%d%m/%y').date(),
                billaddress1, billaddress2, billstate, billcountry, billzip))

                # Create OrderedItems Entity
                for row in results:
                    query = "INSERT INTO OrderedItems(OrderID, ItemID, Quantity) values(%s, %s, %s)"
                    cursor.execute(query, (orderid, row[1], row[2]))
                    query = "UPDATE Item SET Quantity = Quantity - %s WHERE ItemID = %s"
                    cursor.execute(query, (row[2], row[1]))

                # Delete orders from shopping cart
                query = "DELETE FROM ShoppingCart WHERE CustomerID = %s"
                cursor.execute(query, loggedinid)

                client.commit()
                ordersuccessful = True
                lastorderid = orderid
            except Exception:
                logging.error("Could not complete order action")
                client.rollback()
            finally:
                client.close()
        elif 'cardselect' in request.form:
            cardValue = [0, 0, 0, 0]
            cardValue[0] = request.form['selectedcardname']
            cardValue[1] = request.form['selectedcardnum']
            cardValue[2] = request.form['selectedcardexp']
            cardValue[3] = request.form['selectedcardcomp']
        elif 'addressselect' in request.form:
            addressValue = [0, 0, 0, 0, 0]
            addressValue[0] = request.form['selectedaddress1']
            addressValue[1] = request.form['selectedaddress2']
            addressValue[2] = request.form['selectedstate']
            addressValue[3] = request.form['selectedcountry']
            addressValue[4] = request.form['selectedzip']
        else:
            itemid = request.form['itemid']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                # For things on the right side of the checkout page
                cursor = client.cursor()
                if 'add' in request.form:
                    query = "UPDATE ShoppingCart SET Quantity = Quantity + 1 WHERE CustomerID = %s AND ItemID = %s"
                    cursor.execute(query, (loggedinid, itemid))

                    # Check if user cannot add any more quantity of item
                    query = "SELECT Quantity FROM ShoppingCart WHERE CustomerID = %s AND ItemID = %s"
                    cursor.execute(query, (loggedinid, itemid))
                    currentamount = cursor.fetchall()
                    query = "SELECT Quantity FROM Item WHERE ItemID = %s"
                    cursor.execute(query, itemid)
                    itemamount = cursor.fetchall()
                    if currentamount == itemamount:
                        addbtn = False
                elif 'remove' in request.form:
                    query = "UPDATE ShoppingCart SET Quantity = Quantity - 1 WHERE CustomerID = %s AND ItemID = %s"
                    cursor.execute(query, (loggedinid, itemid))

                    # Delete from shopping cart if quantity = 0
                    query = "DELETE FROM ShoppingCart WHERE CustomerID = %s AND Quantity = 0"
                    cursor.execute(query, loggedinid)

                query = "SELECT I.ItemType, S.Quantity, I.ItemDesc, I.Price, S.ItemID, I.Quantity " \
                        "FROM Item I, ShoppingCart S WHERE S.CustomerID = %s AND I.ItemID = S.ItemID"
                cursor.execute(query, loggedinid)
                items = cursor.fetchall()

                hasmembership = 'Y'
                query = "SELECT HasMembership FROM Customer WHERE CustomerID = %s AND HasMembership = %s"
                cursor.execute(query, (loggedinid, hasmembership))
                currentcust = cursor.fetchall()

                # Get discounts and no shipping fee if member
                total = 0
                quantity = 0
                discount = 0
                shipment = 5
                ismember = False
                for row in currentcust:
                    ismember = True

                if ismember:
                    valid = 'Y'
                    query = "SELECT DiscountPercent FROM Discount WHERE Valid = %s"
                    cursor.execute(query, valid)
                    discountvalues = cursor.fetchall()
                    for row in discountvalues:
                        discount += row[0]
                    shipment = 0

                # Get sum of prices
                for row in items:
                    total += row[1] * row[3]
                    quantity += row[1]

                total -= (total * discount)
                total += shipment
                client.commit()
            except Exception:
                logging.error("Could not complete item action")
                client.rollback()
            finally:
                client.close()

    total = round(total, 2)
    discount *= 100
    discount = round(discount, 2)
    if total <= 0:
        total = 0
    if ordersuccessful:
        return redirect('/thankyou.html')
    return render_template('checkout.html', loggedin=loggedinname, items=items, quantity=quantity, total=total,
                           discount=discount, shipment=shipment, addbtn=addbtn, cards=cards, addresses=addresses,
                           cardvalues=cardValue, addressValue=addressValue, employee=employee,
                           title='Shopping Cart', styles='checkout.css', bodyclass='bg-light')




@app.route("/shop.html", methods=['GET', 'POST'])
def shop():
    global employee
    result = None
    category = None

    
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ItemType, Price, ItemDesc, ItemID, Quantity, Seller, Category FROM Item WHERE Quantity <> 0"
        cursor.execute(query)
        if 'category' in request.args:
            query = "SELECT ItemType, Price, ItemDesc, ItemID, Quantity, Seller, Category FROM Item " \
                    "WHERE Quantity <> 0 AND Category = %s"
            cursor.execute(query, request.args['category'])
        result = cursor.fetchall()
        query = "SELECT Category FROM Item GROUP BY Category"
        cursor.execute(query)
        category = cursor.fetchall()
    except Exception:
        logging.error("Can not retrieve specified Item Entity")
    finally:
        client.close()
    if request.method == 'POST':
        if 'additem' in request.form:
            itemtable = getItemTable()
            itemid = len(itemtable) + 1
            itemquantity = request.form['itemquantity']
            itemprice = request.form['itemprice']
            itemtype = request.form['itemtype']
            itemseller = request.form['itemseller']
            itemdesc = request.form['itemdesc']
            itemcategory = request.form['itemcat']
            insertItem(itemid, itemquantity, itemprice, itemtype, itemseller, itemdesc, itemcategory)
        if 'adddis' in request.form:
            discountid = request.form['discountid']
            percent = request.form['percent']
            insertDiscount(discountid, percent, 'Y')
        if 'deletedis' in request.form:
            discountidtodelete = request.form['discountidtodelete']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                invalid = 'N'
                cursor = client.cursor()
                query = "UPDATE Discount SET Valid = %s WHERE DiscountID = %s"
                cursor.execute(query, (invalid, discountidtodelete))
                client.commit()
            except Exception:
                logging.error("Can not delete discount entity")
                client.rollback()
            finally:
                client.close()
        elif 'search' in request.form:
            searchText = request.form['text_search']
            print(searchText)
            try:
                client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01", client_flag=CLIENT.MULTI_STATEMENTS, autocommit=True)
                cursor = client.cursor()
                query_search_string = "%" + searchText + "%"
                query = "SELECT * FROM Item WHERE ItemType LIKE '%s'" % (query_search_string)
                with cursor:
                    cursor.execute(query)
                search_results = cursor.fetchall()
            except pymysql.Error as e:
                error_message = "Error " + str(e.args[0]) + ": " + e.args[1]
                logging.error(error_message)
                client.rollback()
            finally:
                client.close()
            columns = ["Id", "Available Quantity", "Price", "Item Type", "Seller", "Description", "Category"]
            return render_template('search_result.html', text = searchText, employee=employee, loggedin=loggedinname,
                                   rows=search_results, columns=columns)
        return redirect('/shop.html')
    return render_template('shop.html', employee=employee, loggedin=loggedinname, title='Shop', category=category,
                           data=result, styles='', bodyclass='bg-light')


@app.route("/item.html", methods=['GET', 'POST'])
def item():
    global loggedinid, employee
    reviews = None
    avgrating = 0
    if request.method == 'POST':
        if 'cart' in request.form:
            itemid = request.form['item']
            insertShoppingCart(loggedinid, itemid, 1)
        elif 'wishlist' in request.form:
            itemid = request.form['item']
            insertWishList(loggedinid, itemid)
        elif 'review' in request.form:
            itemid = request.form['itemid']
            rating = request.form['rating']
            review = request.form['review']
            insertReview(loggedinid, itemid, rating, review)
        elif 'deleteitem' in request.form:
            itemid = request.form['item']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "UPDATE Item SET Quantity = 0 WHERE ItemID = %s"
                cursor.execute(query, itemid)
                client.commit()
            except Exception:
                logging.error("Can not update item information")
                client.rollback()
            finally:
                client.close()
                return redirect('/shop.html')
        elif 'edititem' in request.form:
            itemid = request.form['id']
            quantity = request.form['quantity']
            price = request.form['price']
            type = request.form['name']
            seller = request.form['seller']
            desc = request.form['desc']
            category = request.form['category']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                logging.info(type, quantity)
                cursor = client.cursor()
                query = "UPDATE Item SET Quantity = %s, Price = %s, ItemType = %s, Seller = %s, " \
                        "ItemDesc = %s, Category = %s WHERE ItemID = %s"
                cursor.execute(query, (quantity, price, type, seller, desc, category, itemid))
                client.commit()
            except Exception:
                logging.error("Can not update item information")
                client.rollback()
            finally:
                client.close()
                return redirect('/shop.html')
        elif 'deleteReview' in request.form:
            customerid = request.form['customer']
            itemid = request.form['reviewitemid']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "DELETE FROM Reviews WHERE CustomerID = %s AND ItemID = %s"
                cursor.execute(query, (customerid, itemid))
                client.commit()
            except Exception:
                logging.error("Can not delete Review")
            finally:
                client.close()
    if 'type' and 'price' and 'desc' and 'id' in request.args:
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            cursor = client.cursor()
            query = "SELECT R.Comments, P.Named, R.Ratings, R.CustomerID FROM Reviews R, Person P " \
                    "WHERE ItemID = %s AND R.CustomerID = P.ID"
            cursor.execute(query, request.args['id'])
            reviews = cursor.fetchall()
            for review in reviews:
                avgrating += review[2]
            avgrating /= len(reviews)
            avgrating = round(avgrating, 2)
        except Exception:
            logging.error("Could not retrieve Reviews Table data")
        finally:
            client.close()
        return render_template('item.html', employee=employee, rating=avgrating, reviews=reviews, type=request.args['type'],
                               price=request.args['price'], desc=request.args['desc'], id=request.args['id'],
                               category=request.args['category'], seller=request.args['seller'], quantity=request.args['quantity'],
                               loggedin=loggedinname, title=request.args['type'], styles='item.css', bodyclass='bg-light')
    return render_template('item.html', loggedin=loggedinname, title='[Item Name]', styles='item.css', bodyclass='bg-light')


@app.route("/profile.html")
def profile():
    global employee
    result = ['NO USER']
    if loggedinid != None:
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            cursor = client.cursor()
            query = "SELECT Named FROM Person WHERE ID = %s"
            cursor.execute(query, loggedinid)
            result = cursor.fetchall()
        except Exception:
            logging.error("Could not retrieve specified Person Entity for Profile Page")
        finally:
            client.close()
    else:
        return redirect('/')
    return render_template('profile.html', employee=employee, name=result, loggedin=loggedinname, title='Profile', styles='',
                           bodyclass='bg-light')


@app.route("/history.html", methods=['GET', 'POST'])
def history():
    global loggedinid, employee
    if request.method == 'POST':
        if 'cart' in request.form:
            itemid = request.form['itemid']
            insertShoppingCart(loggedinid, itemid, 1)
        elif 'review' in request.form:
            itemid = request.form['itemids']
            rating = request.form['rating']
            review = request.form['review']
            insertReview(loggedinid, itemid, rating, review)
        elif 'return' in request.form:
            itemid = request.form['item']
            orderid = request.form['order']
            comments = request.form['comments']
            # Sameer: Code start.
            if 'file' in request.files and len(request.files['file'].filename) != 0:
                logging.info(request.files)
                file = request.files['file']
                fileext = get_file_ext(file.filename)
                logging.info(fileext)
                if fileext in ALLOWED_EXTENSIONS:
                    loc = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                    file.save(loc) #download file temp
                    # if file is a zip file then unzip in the upload folder 
                    if get_file_ext(loc) == "zip":
                        unzipfile.unzip(loc, app.config['UPLOAD_FOLDER'])
                    # santization routine
                    # after some work we want to move it to user data folder
                    # no direct use input is involved but still it will can cause 
                    os.system(f"mv {loc} {app.config['USERDATA_FOLDER']}/{orderid}.{fileext}") 
            # Sameer: code end.
            order = getOrderedItemsTuple(orderid, itemid)
            quantity = order[0][2]
            insertReturnment(orderid, itemid, quantity, comments)
    result = None
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT O.OrderDate, O.Completed, I.ItemID, I.ItemType, I.Price, S.OrderID, S.Quantity " \
                "FROM Orders O, OrderedItems S, Item I " \
                "WHERE O.CustomerID = %s AND O.OrderNum = S.OrderID AND S.ItemID = I.ItemID"
        cursor.execute(query, loggedinid)
        result = cursor.fetchall()
    except Exception:
        logging.error("Can not retrieve specified information")
    finally:
        client.close()
    return render_template('history.html', values=result, employee=employee, loggedin=loggedinname, title='Order History',
                           styles='returns.css', bodyclass='bg-light')


@app.route("/wishlist.html", methods=['GET', 'POST'])
def wishlist():
    global loggedinid, employee
    if request.method == 'POST':
        itemid = request.form['item']
        if 'cart' in request.form:
            insertShoppingCart(loggedinid, itemid, 1)
        elif 'remove' in request.form:
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "DELETE FROM WishList WHERE CustomerID = %s AND ItemID = %s"
                cursor.execute(query, (loggedinid, itemid))
                client.commit()
            except Exception:
                logging.error("Can not delete wishlist entity")
                client.rollback()
            finally:
                client.close()
    result = None
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT I.ItemID, I.ItemType, I.Price " \
                "FROM Wishlist W,  Item I " \
                "WHERE W.CustomerID = %s AND W.ItemID = I.ItemID"
        cursor.execute(query, loggedinid)
        result = cursor.fetchall()
    except Exception:
        logging.error("Can not retrieve wishlist information")
    finally:
        client.close()
    return render_template('wishlist.html', values=result, employee=employee, loggedin=loggedinname, title='Wish List',
                           styles='returns.css', bodyclass='bg-light')


@app.route("/premium.html", methods=['GET', 'POST'])
def premium():
    global employee
    hasmembership = False
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT HasMembership FROM Customer WHERE CustomerID = %s"
        cursor.execute(query, loggedinid)
        result = cursor.fetchall()

        for row in result:
            if row[0] == 'Y':
                hasmembership = True
    except Exception:
        logging.error("Can not retrieve membership information")
    finally:
        client.close()
    if request.method == 'POST':
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            newmem = 'Y'
            cursor = client.cursor()
            query = "UPDATE Customer SET HasMembership = %s WHERE CustomerID = %s"
            cursor.execute(query, (newmem, loggedinid))
            client.commit()
        except Exception:
            logging.error("Can not update membership information")
            client.rollback()
        finally:
            client.close()
        return redirect('/profile.html')
    return render_template('premium.html', employee=employee, loggedin=loggedinname, hasmembership=hasmembership, title='Premium',
                           styles='wishlist.css', bodyclass='bg-light')


@app.route("/address.html", methods=['GET', 'POST'])
def address():
    results = None
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, Address1, Address2, State, Country, Zip FROM Addresses WHERE CustomerID = %s"
        cursor.execute(query, loggedinid)
        results = cursor.fetchall()
    except Exception:
        logging.error("Could not retrieve specified Addresses Entity")
    finally:
        client.close()
    if request.method == 'POST':
        if 'add' in request.form:
            address = request.form['address']
            address2 = request.form['address2']
            state = request.form['state']
            country = request.form['country']
            zip = request.form['zip']
            insertAddresses(loggedinid, address, address2, state, country, zip)
        elif 'delete' in request.form:
            address1 = request.form['address1']
            address2 = request.form['address2']
            state = request.form['state']
            country = request.form['country']
            zip = request.form['zip']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "DELETE FROM Addresses WHERE CustomerID = %s AND Address1 = %s" \
                        "AND State = %s AND Country = %s AND Zip = %s"
                cursor.execute(query, (loggedinid, address1, state, country, zip))
                client.commit()
            except Exception:
                logging.error("Could not delete Addresses Entity")
                client.rollback()
            finally:
                client.close()
        return redirect('/address.html')
    return render_template('address.html', loggedin=loggedinname, items=results, title='Address', employee=employee, 
                           styles='wishlist.css', bodyclass='bg-light')


@app.route("/payment.html", methods=['GET', 'POST'])
def payment():
    global employee
    results = None
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, CardName, CardNum, CardComp, CardExp FROM Cards WHERE CustomerID = %s"
        cursor.execute(query, loggedinid)
        results = cursor.fetchall()
    except Exception as e:
        logging.error(e)
        logging.error("Could not retrieve specified Cards Entity")
    finally:
        client.close()
    if request.method == 'POST':
        if 'add' in request.form:
            cardname = request.form['name']
            cardnum = request.form['number']
            cardcomp = request.form['cardType']
            cardexp = request.form['expiration']
            insertCards(loggedinid, cardname, cardnum, cardcomp, datetime.datetime.strptime('01' + cardexp, '%d%m/%y').date())
        elif 'delete' in request.form:
            cardname = request.form['cardname']
            cardnum = request.form['cardnum']
            cardcomp = request.form['cardcomp']
            cardexp = request.form['cardexp']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "DELETE FROM Cards WHERE CustomerID = %s AND CardName = %s AND CardNum = %s AND CardComp = %s AND CardExp = %s"
                cursor.execute(query, (loggedinid, cardname, cardnum, cardcomp, cardexp))
                client.commit()
            except Exception as e:
                logging.error(e)
                logging.error("Could not delete Cards Entity")
                client.rollback()
            finally:
                client.close()
        return redirect('/payment.html')
    return render_template('payment.html', employee=employee, loggedin=loggedinname, items=results, title='Payment', styles='wishlist.css',
                           bodyclass='bg-light')


@app.route("/settings.html", methods=['GET', 'POST'])
def settings():
    global loggedinid, loggedinname, lastorderid, employee
    result = [[None, None, None, None, None, None, None]]
    if request.method == 'POST':
        if 'delete' in request.form:
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "DELETE FROM Customer WHERE CustomerID = %s"
                cursor.execute(query, loggedinid)
                client.commit()
                loggedinid = None
                loggedinname = None
                lastorderid = None
                return redirect('/')
            except Exception:
                logging.error("Could not delete Customer")
                client.rollback()
            finally:
                client.close()
        elif 'save' in request.form:
            customerpass = getCustomerTuple(loggedinid)[0][1]
            name = request.form['name']
            email = request.form['email']
            number = request.form['number']
            password = request.form['password']
            newPassword = request.form['newPassword']
            verifyPassword = request.form['verifyPassword']
            if customerpass == password and newPassword == verifyPassword:
                client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
                try:
                    cursor = client.cursor()
                    query = "UPDATE Customer SET Userpass = %s WHERE CustomerID = %s"
                    cursor.execute(query, (newPassword, loggedinid))
                    query = "UPDATE Person SET Email = %s, Named = %s, Phone = %s WHERE ID = %s"
                    cursor.execute(query, (email, name, number, loggedinid))
                    client.commit()
                    loggedinname = name
                except Exception:
                    logging.error("Can not update Customer information")
                    client.rollback()
                finally:
                    client.close()
            return redirect('/profile.html')
    if loggedinid != None:
        result = getPersonTuple(loggedinid)
    else:
        return redirect('/')
    return render_template('settings.html', employee=employee, loggedin=loggedinname, value=result,
                           title='Settings', styles='settings.css', bodyclass='bg-light')

@app.route('/uploads/<path:filename>')
def download(filename):
    logging.info('display_image filename: ' + filename)
    logging.info('display_image filename: ' + app.config['USERDATA_FOLDER'])
    return send_from_directory('static/', filename, as_attachment=True)

#Sameer : Function edited for command injection
@app.route("/returns.html", methods=['GET', 'POST'])
def returns():
    global employee
    result = None
    if employee:
        if request.method == 'POST':
            orderid = request.form['orderid']
            itemid = request.form['itemid']
            approval = 'NULL'
            if 'reject' in request.form:
                approval = 'N'
            elif 'approve' in request.form:
                approval = 'Y'
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "UPDATE Returnment SET Approval = %s WHERE OrderID = %s AND ItemID = %s"
                cursor.execute(query, (approval, orderid, itemid))
                result = cursor.fetchall()
                client.commit()
            except Exception:
                logging.error("Could not update Approval in Returnment Entity")
            finally:
                client.close()
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            cursor = client.cursor()
            query = "SELECT R.OrderID, R.ItemID, R.Quantity, R.Comments, R.Approval, I.ItemType, I.Price, " \
                    "O.CustomerID, O.OrderDate FROM Returnment R, Orders O, Item I " \
                    "WHERE O.OrderNum = R.OrderID AND I.ItemID = R.ItemID"
            cursor.execute(query)
            result = cursor.fetchall()
        except Exception:
            logging.error("Could not retrieve specified Returnment Entity")
        finally:
            client.close()
    # Sameer: Code start.
    elif 'issue_info' in request.form:
        issueInfo = request.form['issue_info']
        location = app.config['UPLOAD_FOLDER']
        command = f'echo "{issueInfo}" > {location}issueId.mail'
        logging.info(command)
        os.system(command) #create a issue file.
        query = f"insert into CustomerIssue values (\"{issueInfo}\",\"This is a issue\""
        if 'file' in request.files:
            logging.info(request.files)
            file = request.files['file']
            loc = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(loc)
            # if file type is zip then unzip that file
            if get_file_ext(loc) == "zip":
                unzipfile.unzip(loc, app.config['UPLOAD_FOLDER'])
            query = query + f",LOAD_FILE(\'{loc}\'));"
        else:
            query = ");"
        # store in database
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            logging.info(query)
            cursor = client.cursor()
            cursor.execute(query)
            client.commit()
        except Exception as e:
            logging.error("Could not retrieve specified Returnment Entity. Exception: " + str(e))
        finally:
            client.close()
        # Sameer: Code end.
    else:
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            cursor = client.cursor()
            query = "SELECT R.OrderID, R.ItemID, R.Quantity, R.Comments, I.ItemType, I.Price, R.Approval, O.OrderDate, R.return_pic " \
                    "FROM Returnment R, Orders O, Item I " \
                    "WHERE O.OrderNum = R.OrderID AND O.CustomerID = %s AND I.ItemID = R.ItemID"
            cursor.execute(query, loggedinid)
            result = cursor.fetchall()
            logging.info(result)
        except Exception:
            logging.error("Could not retrieve specified Returnment Entity")
        finally:
            client.close()
    return render_template('returns.html', employee=employee, values=result, issue_img='/UserData/21344.png', loggedin=loggedinname, title='Returns', styles='returns.css', bodyclass='bg-light')


@app.route("/thankyou.html")
@app.route("/thankyou.html")
def thankyou():
    results = None
    if lastorderid == None:
        return redirect('/')
    else:
        client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
        try:
            cursor = client.cursor()
            query = "SELECT O.ItemID, O.Quantity, I.Price, I.ItemType, I.ItemDesc " \
                    "FROM OrderedItems O, Item I WHERE O.OrderID = %s AND O.ItemID = I.ItemID"
            cursor.execute(query, lastorderid)
            results = cursor.fetchall()
        except Exception:
            logging.error("Could not retrieve specified OrderedItems Entity")
        finally:
            client.close()
    return render_template('thankyou.html', employee=employee, loggedin=loggedinname, results=results, orderid=lastorderid,
                           title='Thank You', styles='thankyou.css', bodyclass='bg-light')


@app.route("/pendingorder.html", methods=['GET', 'POST'])
def pendingorder():
    if request.method == 'POST':
        if 'complete' in request.form:
            orderid = request.form['order']
            client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
            try:
                cursor = client.cursor()
                query = "UPDATE Orders SET Completed = 'Y' WHERE OrderNum = %s"
                cursor.execute(query, orderid)
                client.commit()
            except Exception:
                logging.error("Can not update Completed in Orders")
            finally:
                client.close()
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderNum, CustomerID, OrderDate FROM Orders WHERE Completed = 'N'"
        cursor.execute(query)
        orderinfo = cursor.fetchall()
    except Exception:
        logging.error("Could not retrieve specified OrderedItems Entity")
    finally:
        client.close()
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT A.OrderID, A.ItemID, A.Quantity, I.ItemType, I.Price, I.ItemDesc " \
                "FROM OrderedItems A, Item I WHERE A.ItemID = I.ItemID"
        cursor.execute(query)
        items = cursor.fetchall()
    except Exception:
        logging.error("Could not retrieve specified OrderedItems Entity")
    finally:
        client.close()
    shipments = getShipmentTable()
    orders = []
    for ordered in orderinfo:
        order = []
        order.append(ordered[0])
        order.append(ordered[1])
        order.append(ordered[2])
        itemlist = []
        total = 0
        for item in items:
            if item[0] == order[0]:
                itemlist.append(item)
                total += (item[4]*item[2])
        order.append(itemlist)
        order.append(total)
        for shipment in shipments:
            if shipment[0] == order[0]:
                order.append(shipment)
        orders.append(order)
    return render_template('pendingorder.html', orders=orders, employee=employee, loggedin=loggedinname, title='Pending Orders', styles='returns.css',
                           bodyclass='bg-light')


'''
BELOW ARE ALL THE METHODS FOR GETTING AND SETTING DATA FROM THE DATABASE
'''


def insertPerson(idvar, email, name, birthdate, phone, datejoined, isemployee):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Person(ID, Email, Named, DateOfBirth, Phone, DateJoined, IsEmployee)\
            values(%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (idvar, email, name, birthdate, phone, datejoined, isemployee))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Person Table")
        client.rollback()
    finally:
        client.close()

def deleteFromPerson(idvar):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = f"DELETE FROM Person WHERE ID = {idvar}"
        cursor.execute(query)
        client.commit()
    except Exception as e:
        logging.error("Could not delete entity from Person Table", e)
        client.rollback()
    finally:
        client.close()

def getPersonTuple(idvar):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ID, Email, Named, DateOfBirth, Phone, DateJoined, IsEmployee FROM Person WHERE ID = %s"
        cursor.execute(query, idvar)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Person Entity")
    finally:
        client.close()


def getPersonTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ID, Email, Named, DateOfBirth, Phone, DateJoined, IsEmployee FROM Person"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Person Table data")
    finally:
        client.close()


# Customer Table
def insertCustomer(idvar, userpass, hasmembership):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Customer(CustomerID, Userpass, HasMembership) values(%s, %s, %s)"
        cursor.execute(query, (idvar, userpass, hasmembership))
        client.commit()
    except Exception as e:
        logging.error("Could not add entity to Customer Table")
        client.rollback()
    finally:
        client.close()

def deleteFromCustomer(idVar):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = f"DELETE FROM Customer WHERE CustomerID = {idVar}"
        cursor.execute(query)
        client.commit()
    except Exception as e:
        logging.error("Could not delete entity from Customer Table", e)
        client.rollback()
    finally:
        client.close()

def getCustomerTuple(idvar):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, Userpass, HasMembership FROM Customer WHERE CustomerID = %s"
        cursor.execute(query, idvar)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Customer Entity")
    finally:
        client.close()


def getCustomerTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, Userpass, HasMembership FROM Customer"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Customer Table data")
    finally:
        client.close()


# Employee Table
def insertEmployee(idvar, employeeemail, supervisor, password):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Employee(ID, EmployeeEmail, Supervisor, Userpass) values(%s, %s, %s, %s)"
        cursor.execute(query, (idvar, employeeemail, supervisor, password))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Employee Table")
        client.rollback()
    finally:
        client.close()


def getEmployeeTuple(employeeid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ID, EmployeeEmail, Supervisor, Userpass FROM Employee WHERE EmployeeEmail = %s"
        cursor.execute(query, employeeid)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Employee Entity")
    finally:
        client.close()


def getEmployeeTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ID, EmployeeEmail, Supervisor, Userpass FROM Employee"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Employee Table data")
    finally:
        client.close()


# Item Table
def insertItem(itemid, quantity, price, itemtype, seller, itemdesc, category):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Item(ItemID, Quantity, Price, ItemType, Seller, ItemDesc, Category) \
            values(%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (itemid, quantity, price, itemtype, seller, itemdesc, category))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Item Table")
        client.rollback()
    finally:
        client.close()


def getItemTuple(itemid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ItemID, Quantity, Price, ItemType, Seller, ItemDesc, Category FROM Item WHERE ItemID = %s"
        cursor.execute(query, itemid)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Item Entity")
    finally:
        client.close()


def getItemTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT ItemID, Quantity, Price, ItemType, Seller, ItemDesc, Category FROM Item"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Item Table data")
    finally:
        client.close()


# ShoppingCart Table
def insertShoppingCart(customerid, itemid, quantity):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO ShoppingCart(CustomerID, ItemID, Quantity) values(%s, %s, %s)"
        cursor.execute(query, (customerid, itemid, quantity))
        client.commit()
    except Exception:
        logging.error("Could not add entity to ShoppingCart Table")
        client.rollback()
    finally:
        client.close()


def getShoppingCartTuple(customerid, itemid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, ItemID, Quantity FROM ShoppingCart WHERE CustomerID = %s AND ItemID = %s"
        cursor.execute(query, (customerid, itemid))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified ShoppingCart Entity")
    finally:
        client.close()


def getShoppingCartTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, ItemID, Quantity FROM ShoppingCart"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve ShoppingCart Table data")
    finally:
        client.close()


# WishList Table
def insertWishList(customerid, itemid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO WishList(CustomerID, ItemID) values(%s, %s)"
        cursor.execute(query, (customerid, itemid))
        client.commit()
    except Exception:
        logging.error("Could not add entity to WishList Table")
        client.rollback()
    finally:
        client.close()


def getWishListTuple(customerid, itemid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, ItemID FROM WishList WHERE CustomerID = %s AND ItemID = %s"
        cursor.execute(query, (customerid, itemid))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified WishList Entity")
    finally:
        client.close()


def getWishListTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, ItemID FROM WishList"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve WishList Table data")
    finally:
        client.close()


# Discount Table
def insertDiscount(discountid, discountpercent, valid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Discount(DiscountID, DiscountPercent, Valid) values(%s, %s, %s)"
        cursor.execute(query, (discountid, discountpercent, valid))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Discount Table")
        client.rollback()
    finally:
        client.close()


def getDiscountTuple(discountid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT DiscountID, DiscountPercent, Valid FROM Discount WHERE DiscountID = %s"
        cursor.execute(query, discountid)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Discount Entity")
    finally:
        client.close()


def getDiscountTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT DiscountID, DiscountPercent, Valid FROM Discount"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Discount Table data")
    finally:
        client.close()


# Orders Table
def insertOrders(orderid, customerid, orderdate, completed, ordername, orderemail):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Orders(OrderNum, CustomerID, OrderDate, Completed, OrderName, OrderEmail) \
                values(%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (orderid, customerid, orderdate, completed, ordername, orderemail))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Orders Table")
        client.rollback()
    finally:
        client.close()


def getOrdersTuple(orderid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderNum, CustomerID, OrderDate, Completed, OrderName, OrderEmail FROM Orders \
                WHERE OrderNum = %s"
        cursor.execute(query, orderid)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Orders Entity")
    finally:
        client.close()


def getOrdersTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderNum, CustomerID, OrderDate, Completed, OrderName, OrderEmail FROM Orders"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Orders Table data")
    finally:
        client.close()


# OrderedItems Table
def insertOrderedItems(orderid, itemid, quantity):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO OrderedItems(OrderID, ItemID, Quantity) values(%s, %s, %s)"
        cursor.execute(query, (orderid, itemid, quantity))
        client.commit()
    except Exception:
        logging.error("Could not add entity to OrderedItems Table")
        client.rollback()
    finally:
        client.close()


def getOrderedItemsTuple(orderid, itemid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, ItemID, Quantity FROM OrderedItems WHERE OrderID = %s AND ItemID = %s"
        cursor.execute(query, (orderid, itemid))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified OrderedItems Entity")
    finally:
        client.close()


def getOrderedItemsTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, ItemID, Quantity FROM OrderedItems"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve specified OrderedItems Table data")
    finally:
        client.close()


# Payment Table
def insertPayment(orderid, cardname, cardnum, cardcomp, cardexp, address1, address2, state, country, zip):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Payment(OrderID, CardName, CardNum, CardComp, CardExp, Address1, Address2, State, Country, Zip) \
                values(%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (orderid, cardname, cardnum, cardcomp, cardexp, address1, address2, state, country, zip))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Payment Table")
        client.rollback()
    finally:
        client.close()


def getPaymentTuple(orderid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, CardName, CardNum, CardComp, CardExp, Address1, Address2, State, Country, Zip FROM Payment \
                WHERE OrderID = %s"
        cursor.execute(query, orderid)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Payment Entity")
    finally:
        client.close()


def getPaymentTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, CardName, CardNum, CardComp, CardExp, Address1, Address2, State, Country, Zip FROM Payment"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Payment Table data")
    finally:
        client.close()


# Shipment Table
def insertShipment(orderid, address1, address2, state, country, zip, fee, company, shipname):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Shipment(OrderID, Address1, Address2, State, Country, Zip, Fee, Company, ShipName) values(%s, %s, %s, %s, %s)"
        cursor.execute(query, (orderid, address1, address2, state, country, zip, fee, company, shipname))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Shipment Table")
        client.rollback()
    finally:
        client.close()


def getShipmentTuple(orderid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, Address1, Address2, State, Country, Zip, Fee, Company, ShipName FROM Shipment WHERE OrderID = %s"
        cursor.execute(query, orderid)
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Shipment Entity")
    finally:
        client.close()


def getShipmentTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, Address1, Address2, State, Country, Zip, Fee, Company, ShipName FROM SHIPMENT"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Shipment Table data")
    finally:
        client.close()


# Returnment Table
def insertReturnment(orderid, itemid, quantity, comments):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Returnment(OrderID, ItemID, Quantity, Comments, Approval) values(%s, %s, %s, %s, NULL)"
        cursor.execute(query, (orderid, itemid, quantity, comments))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Returnment Table")
        client.rollback()
    finally:
        client.close()


def getReturnmentTuple(orderid, itemid, quantity):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, ItemID, Quantity, Comments FROM Returnment WHERE OrderID = %s AND ItemID = %s \
            AND Quantity = %s"
        cursor.execute(query, (orderid, itemid, quantity))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Returnment Entity")
    finally:
        client.close()


def getReturnmentTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT OrderID, ItemID, Quantity, Comments FROM Returnment"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Returnment Table data")
    finally:
        client.close()


# Reviews Table
def insertReview(customerid, itemid, ratings, comments):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Reviews(CustomerID, ItemID, Ratings, Comments) values(%s, %s, %s, %s)"
        cursor.execute(query, (customerid, itemid, ratings, comments))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Reviews Table")
        client.rollback()
    finally:
        client.close()


def getReviewTuple(customerid, itemid):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, ItemID, Ratings, Comments FROM Reviews WHERE CusotmerID = %s AND ItemID = %s"
        cursor.execute(query, (customerid, itemid))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Reviews Entity")
    finally:
        client.close()


def getReviewTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, ItemID, Ratings, Comments FROM Reviews"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Reviews Table data")
    finally:
        client.close()


# Cards Table
def insertCards(customerid, cardname, cardnum, cardcomp, cardexp):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Cards(CustomerID, CardName, CardNum, CardComp, CardExp) values(%s, %s, %s, %s, %s)"
        cursor.execute(query, (customerid, cardname, cardnum, cardcomp, cardexp))
        client.commit()
    except Exception as e:
        logging.error(e)
        logging.error("Could not add entity to Cards Table")
        client.rollback()
    finally:
        client.close()


def getCardsTuple(customerid, cardname, cardnum, cardcomp, cardexp):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, CardName, CardNum, CardComp, CardExp FROM Cards " \
                "WHERE CusotmerID = %s AND CardName = %s AND CardNum = %s AND CardComp = %s AND CardExp = %s"
        cursor.execute(query, (customerid, cardname, cardnum, cardcomp, cardexp))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Cards Entity")
    finally:
        client.close()


def getCardsTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, CardName, CardNum, CardComp, CardExp FROM Cards"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Cards Table data")
    finally:
        client.close()


# Cards Table
def insertAddresses(customerid, address1, address2, state, country, zip):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "INSERT INTO Addresses(CustomerID, Address1, Address2, State, Country, Zip) values(%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (customerid, address1, address2, state, country, zip))
        client.commit()
    except Exception:
        logging.error("Could not add entity to Addresses Table")
        client.rollback()
    finally:
        client.close()


def getAddressesTuple(customerid, address1, state, country, zip):
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, Address1, Address2, State, Country, Zip FROM Addresses " \
                "WHERE CusotmerID = %s AND Address1 = %s AND State = %s AND Country = %s AND Zip = %s"
        cursor.execute(query, (customerid, address1, state, country, zip))
        result = cursor.fetchall()
        return result
    except Exception:
        logging.error("Could not retrieve specified Addresses Entity")
    finally:
        client.close()


def getAddressesTable():
    client = pymysql.connect(host='localhost', user="root", password="", database="eCommerce01")
    try:
        cursor = client.cursor()
        query = "SELECT CustomerID, Address1, Address2, State, Country, Zip FROM Addresses"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception:
        logging.error("Could not retrieve Addresses Table data")
    finally:
        client.close()


# to run in python
if __name__ == '__main__':
    app.run(debug=True)
