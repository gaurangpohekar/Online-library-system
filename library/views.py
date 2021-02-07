import json
import urllib.request

from bson.objectid import ObjectId
from django.http import JsonResponse
from django.shortcuts import HttpResponse, redirect
from django.shortcuts import render
from django.views.generic import View
from pymongo import MongoClient
from datetime import datetime

from .forms import *

loggedIn = False
client = MongoClient(
    "mongodb+srv://Application:application1234@onlib.i34wm.mongodb.net/data?retryWrites=true&w=majority")
db = client.data


# Create your views here.
class mainPage(View):
    def get(self, request, id):
        users = db['Users']
        userdata = users.find_one({"_id": ObjectId(id)})
        email = userdata['email']
        self.updateBookStatus(email)
        addMembership.updateMembership()
        membership = db['membership']
        mem = membership.find_one({"email": email})
        memdata = dict()
        if mem is None:
            addMembership.addMember(email, "Free", "infinite")
            mem = membership.find_one({"email": email})
        for i in mem.keys():
            if i != "_id":
                memdata[i] = mem[i]
        return render(request, 'main.html', {'id': id, 'email': email, "mem": mem})

    def updateBookStatus(self, email):
        borrowed = db['borrowed']
        with urllib.request.urlopen("http://worldtimeapi.org/api/timezone/Asia/Kolkata") as url:
            data = json.loads(url.read().decode())
            dat = data['datetime'].split("T")[0]
            today = datetime.strptime(dat, "%Y-%m-%d")
            bl = borrowed.find_one({'email': email})
            if bl is None:
                objdict = {"email": email, "books": list()}
                borrowed.insert_one(objdict)
                bl = borrowed.find_one({'email': email})
            bl = bl['books']
            temp = list()
            for i in bl:
                dat2 = i['date']
                dat2 = datetime.strptime(dat2, "%Y-%m-%d")
                nodays = abs((today - dat2).days)
                if nodays > 7:
                    nodays = 0
                else:
                    nodays = 7 - nodays
                bookobj = i
                bookobj['days'] = nodays
                if nodays == 0:
                    bookobj['expired'] = True
                temp.append(bookobj)
            borrowed.update_one({"email": email}, {"$set": {"books": temp}})


class IndexView(View):
    def get(self, request):
        return render(request, 'midecontent.html')


class LoginForm(View):
    form_class = loginForm

    def get(self, request):
        form = self.form_class()
        return render(request, 'login.html', {'form': form})

    def post(self, request):
        users = db['Users']
        email = request.POST.get('email')
        password = request.POST.get('password')
        if self.authenticate(db, email, password):
            userdict = users.find_one({"email": email})
            return redirect('main/' + str(userdict['_id']) + "/")
        return HttpResponse('Failed')

    def authenticate(self, db, email, passwd):
        users = db['Users']
        userdict = users.find_one({"email": email})
        if userdict is None:
            return False
        if userdict['password'] == passwd:
            loggedIn = True
            return True
        return False


class SignUp(View):
    form_class = SignUpForm

    def get(self, request):
        form = self.form_class()
        return render(request, 'SignUp.html', {'popup': False, 'form': form})

    def post(self, request):
        users = db['Users']
        lists = db['lists']
        message = ''
        fname = request.POST.get('fname')
        lname = request.POST.get('lname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        address = request.POST.get('address')
        userdata = {'fname': fname, 'lname': lname, 'email': email, 'password': password,
                    'address': address}
        listobj = {'email': email, 'books': list()}
        user = users.find_one({'email': email})
        if user is None:
            users.insert_one(userdata)
            lists.save(listobj)
            message = "Successfully registered"
        else:
            message = "User already exists"
        addMembership.addMember(email, "Free", "Infinite")
        return render(request, 'SignUp.html', {'popup': True, 'message': message})


class getList(View):
    def get(self, request, objid):
        lists = db['lists']
        users = db['Users']
        bookdb = db['books']
        email = users.find_one({"_id": ObjectId(objid)})
        email = email['email']
        listobj = lists.find_one({'email': email})
        books = listobj['books']
        templist = list()
        for i in books:
            templist.append(bookdb.find_one({"_id": i}))
        if listobj is None:
            return JsonResponse({"error": "Not found"})
        return JsonResponse(templist, safe=False)


class getuser(View):
    def get(self, request, id):
        users = db["Users"]
        userdata = users.find_one({"_id": ObjectId(id)})
        temp = dict()
        for i in userdata.keys():
            if i != "_id":
                temp[i] = userdata[i]
        return JsonResponse(temp)


class getCatalogue(View):
    def get(self, request):
        books = db['books']
        userdata = books.find({})
        userdata = list(userdata)
        return JsonResponse(userdata, safe=False)


class searchTitle(View):
    def get(self, request, title):
        books = db['books']
        userdata = books.find({"title": {"$regex": title, "$options": 'i'}})
        userdata = list(userdata)
        return JsonResponse(userdata, safe=False)


class getBook(View):
    def get(self, request, id, email):
        books = db['books']
        membership = db['membership']
        bookdata = books.find_one({"_id": id})
        if bookdata is None:
            return HttpResponse("404 Page not found")
        datapass = dict()
        datapass['bookid'] = id
        datapass['imglink'] = bookdata['cover']['medium']
        datapass['title'] = bookdata['title']
        datapass['description'] = bookdata['description']
        datapass['email'] = email
        lists = db['lists']
        listobj = lists.find_one({"email": email})
        arr = listobj['books']
        if id in arr:
            datapass['dis'] = "true"
        else:
            datapass['dis'] = "false"
        stat = self.checkExpired(id, email)
        datapass['expired'] = stat['expired']
        datapass['days'] = stat['days']
        return render(request, 'bookview.html', datapass)

    def checkExpired(self, id, email):
        borrowed = db['borrowed']
        bd = borrowed.find_one({"email": email})
        if bd is None:
            return {"expired": True, "days": 0}
        bl = bd['books']
        for i in bl:
            if i['bookid'] == id and not i['expired']:
                return {"expired": i['expired'], "days": i['days']}
        return {"expired": True, "days": 0}


class addTolist(View):
    def get(self, request, email, id):
        books = db['books']
        lists = db['lists']
        bookdata = books.find_one({"_id": id})
        listdata = lists.find_one({"email": email})
        if bookdata is None or listdata is None:
            return JsonResponse({"Status": "Book was not added"})
        else:
            if id not in listdata['books']:
                templist = listdata['books']
                templist.append(id)
                lists.update_one({"email": email}, {"$set": {"books": templist}})
                return JsonResponse({"status": "Book was added"})
        return JsonResponse({"status": "Book already present"})


class removeFromList(View):
    def get(self, request, email, id):
        books = db['books']
        lists = db['lists']
        bookdata = books.find_one({"_id": id})
        listdata = lists.find_one({"email": email})
        if bookdata is None or listdata is None:
            return JsonResponse({"Status": "Book was not removed"})
        else:
            if id in listdata['books']:
                templist = listdata['books']
                templist.remove(id)
                lists.update_one({"email": email}, {"$set": {"books": templist}})
                return JsonResponse({"status": "Book was removed"})
        return JsonResponse({"status": "Book was not present in the list"})


class getAuthor(View):
    def get(self, request, id):
        authors = db['authors']
        au = authors.find_one({"_id": id})
        if au is None:
            return JsonResponse({"status": "Not found"})
        return JsonResponse({"name": au['Name']})


class borrow(View):
    def get(self, request, id, email):
        borrowed = db['borrowed']
        books = db['books']
        bl = borrowed.find_one({"email": email})
        if bl is None:
            borrowed.insert({"email": email, "books": list()})
            bl = borrowed.find_one({"email": email})
        bk = books.find_one({"_id": id})
        if bk is None:
            return JsonResponse({"status": "error"})
        else:
            with urllib.request.urlopen("http://worldtimeapi.org/api/timezone/Asia/Kolkata") as url:
                data = json.loads(url.read().decode())
                dat = data['datetime'].split("T")[0]
                td = {"bookid": id, "date": dat, "expired": False, "days": 7}
                tlist = bl['books']
                tlist.append(td)
                borrowed.update_one({"email": email}, {'$set': {"books": tlist}})
        return JsonResponse({"status": "Success"})


class getUserProfile(View):
    def get(self, request, id):
        users = db['Users']
        userdata = users.find_one({"_id": ObjectId(id)})
        temp = dict()
        for i in userdata.keys():
            if i != "_id":
                temp[i] = userdata[i]
        email = temp['email']
        membership = db['membership']
        mem = membership.find_one({"email": email})
        memdata = dict()
        if mem is None:
            addMembership.addMember(email, "Free", "infinite")
            mem = membership.find_one({"email": email})
        for i in mem.keys():
            if i != "_id":
                memdata[i] = mem[i]
        return render(request, 'profile.html', {'user': temp, 'mem': memdata})


class addMembership(View):

    def get(self, request, email, type1, time):
        self.updateMembership()
        membership = db['membership']
        mem = membership.find_one({"email": email})
        if mem is not None and mem['type'] != "Free":
            return JsonResponse({"status": "A membership is already active"})
        with urllib.request.urlopen("http://worldtimeapi.org/api/timezone/Asia/Kolkata") as url:
            data = json.loads(url.read().decode())
            dat = data['datetime'].split("T")[0]
            memdict = {"email": email, "type": type1, "date": dat, "validity": time}
            if type1 == "Gold":
                memdict['remaining'] = time * 30
            else:
                memdict['remaining'] = "unlimited"
            if mem is not None and mem['type'] == "Free":
                membership.replace_one({"email": email}, memdict)
            elif mem is None:
                membership.insert_one(memdict)
        return JsonResponse({"status": "Success!"})

    @staticmethod
    def updateMembership():
        membership = db['membership']
        with urllib.request.urlopen("http://worldtimeapi.org/api/timezone/Asia/Kolkata") as url:
            data = json.loads(url.read().decode())
            dat = data['datetime'].split("T")[0]
            dat1 = datetime.strptime(dat, "%Y-%m-%d")
            memlist = membership.find({"type": "Gold"})
            for i in memlist:
                time = i['validity']
                dat2 = i['date']
                dat2 = datetime.strptime(dat2, "%Y-%m-%d")
                if abs((dat1 - dat2).days) < (time * 30):
                    upd = (time*30) -abs((dat1 - dat2).days)
                    membership.update({"email": i['email']}, {"$set": {"remaining": upd}})
                else:
                    membership.replace_one({"email": i['email']}, {"email": i['email'], 'type': "Free", 'date': dat,
                                                                   'validity': 'infinite', 'remaining': 'unlimited'})

    @staticmethod
    def addMember(email, type1, time):
        addMembership.updateMembership()
        membership = db['membership']
        mem = membership.find_one({"email": email})
        print(mem)
        if mem is not None and mem['type'] != "Free":
            return JsonResponse({"status": "A membership is already active"})
        with urllib.request.urlopen("http://worldtimeapi.org/api/timezone/Asia/Kolkata") as url:
            data = json.loads(url.read().decode())
            dat = data['datetime'].split("T")[0]
            memdict = {"email": email, "type": type1, "date": dat, "validity": time}
            if type1 == "Gold":
                memdict['remaining'] = time * 30
            else:
                memdict['remaining'] = "unlimited"
            if mem is not None and mem['type'] == "Free":
                membership.replace_one({"email": email}, memdict)
            elif mem is None:
                membership.insert_one(memdict)


def getBorrowedBooks(request, email):
    borrowed = db['borrowed']
    bu = borrowed.find_one({'email': email})
    if bu is not None:
        borrowList = bu['books']
        activeList = list()
        expiredlist = list()
        for i in borrowList:
            bd = i
            tempData = getJsonBook(i['bookid'])
            for m in tempData.keys():
                bd[m] = tempData[m]
            date = datetime.strptime(i['date'], "%Y-%m-%d")
            bd['date'] = date.strftime("%d %b %Y")
            if i['expired']:
                expiredlist.append(bd)
            else:
                activeList.append(bd)
        return JsonResponse({"active": activeList, "expired": expiredlist})
    return JsonResponse({"active": list(), "expired": list()})


def getJsonBook(id):
    books = db['books']
    bookdata = books.find_one({"_id": id})
    if bookdata is None:
        return None
    datapass = dict()
    datapass['imglink'] = bookdata['cover']['medium']
    datapass['title'] = bookdata['title']
    return datapass
