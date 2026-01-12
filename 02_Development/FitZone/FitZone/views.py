
from django.shortcuts import render

def home(request):
    return render(request,'index.html')
def dashboard(request):
    return render(request,'dashboard.html')
def trainer(request):
    return render(request,'trainer/trainer.html')

def dashboard(request):
    return render(request, 'userdashboard.html')

    

    