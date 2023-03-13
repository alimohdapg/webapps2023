from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy

from payapp.forms import PaymentForm
from payapp.models import Account, convert_currency, Transaction


def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return render(request, 'payapp/home.html')
        account = Account.objects.get(user=request.user)
        if account.currency == 'USD':
            currency_sign = '$'
        elif account.currency == 'EUR':
            currency_sign = '€'
        else:
            currency_sign = '£'
        return render(request, 'payapp/home.html', {'balance': f'{currency_sign}{"{:.2f}".format(account.balance)}'})
    return render(request, 'payapp/home.html')


@user_passes_test(lambda u: not u.is_staff, login_url=reverse_lazy('logout_user'))
@transaction.atomic
@login_required(login_url='/register/login_user')
def send_payment(request):
    if request.method == 'POST':
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            new_transaction = payment_form.save(commit=False)
            sender = request.user.account
            if sender.balance < new_transaction.amount:
                payment_form.add_error('amount', 'Insufficient balance')
                return render(request, 'payapp/send_payment.html', {'payment_form': payment_form})
            receiver = User.objects.get(email__exact=payment_form.cleaned_data['recipient_email']).account
            sender.balance -= new_transaction.amount
            receiver.balance += convert_currency(sender.currency, receiver.currency, new_transaction.amount)
            sender.save()
            receiver.save()
            new_transaction.sender = sender
            new_transaction.receiver = receiver
            new_transaction.save()
            return render(request, 'payapp/send_payment.html',
                          {'payment_sent': True, 'payment_form': payment_form})
        else:
            return render(request, 'payapp/send_payment.html', {'payment_form': payment_form})
    else:
        payment_form = PaymentForm()
    return render(request, 'payapp/send_payment.html', {'payment_form': payment_form})


@user_passes_test(lambda u: not u.is_staff, login_url=reverse_lazy('logout_user'))
@transaction.atomic
@login_required(login_url='/register/login_user')
def request_payment(request):
    if request.method == 'POST':
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            new_transaction = payment_form.save(commit=False)
            new_transaction.request = True
            new_transaction.sender = request.user.account
            new_transaction.receiver = User.objects.get(
                email__exact=payment_form.cleaned_data['recipient_email']).account
            new_transaction.save()
            return render(request, 'payapp/request_payment.html',
                          {'request_sent': True, 'payment_form': payment_form})
        else:
            return render(request, 'payapp/request_payment.html', {'payment_form': payment_form})
    else:
        payment_form = PaymentForm()
    return render(request, 'payapp/request_payment.html', {'payment_form': payment_form})


@user_passes_test(lambda u: not u.is_staff, login_url=reverse_lazy('logout_user'))
@login_required(login_url='/register/login_user')
def requests(request):
    sent_requests = list(Transaction.objects.filter(sender=request.user.account, request=True).order_by('-modified'))
    received_requests = list(
        Transaction.objects.filter(receiver=request.user.account, request=True).order_by('-modified'))
    return render(request, 'payapp/requests.html',
                  {'sent_requests': sent_requests, 'received_requests': received_requests,
                   'insufficient_balance_id': request.session.get('insufficient_balance_id', -1)})


@user_passes_test(lambda u: not u.is_staff, login_url=reverse_lazy('logout_user'))
@transaction.atomic
@login_required(login_url='/register/login_user')
def delete_request(request):
    new_transaction = Transaction.objects.get(pk=request.GET["request_id"])
    new_transaction.request = False
    new_transaction.save()
    return redirect('requests')


@user_passes_test(lambda u: not u.is_staff, login_url=reverse_lazy('logout_user'))
@transaction.atomic
@login_required(login_url='/register/login_user')
def accept_request(request):
    request_id = request.GET["request_id"]
    new_transaction = Transaction.objects.get(pk=request_id)
    converted_amount = convert_currency(new_transaction.sender.currency, new_transaction.receiver.currency,
                                        new_transaction.amount)
    if new_transaction.receiver.balance < converted_amount:
        request.session['insufficient_balance_id'] = request_id
        return redirect('requests')
    new_transaction.receiver.balance -= converted_amount
    new_transaction.sender.balance += new_transaction.amount
    new_transaction.request = False
    new_transaction.sender.save()
    new_transaction.receiver.save()
    new_transaction.save()
    return redirect('requests')


@user_passes_test(lambda u: not u.is_staff, login_url=reverse_lazy('logout_user'))
@login_required(login_url='/register/login_user')
def history(request):
    transaction_history = list(
        Transaction.objects.filter(
            (Q(sender=request.user.account) | Q(receiver=request.user.account)) & Q(request=False)
        ).order_by('-modified'))
    return render(request, 'payapp/history.html', {'transaction_history': transaction_history})


@user_passes_test(lambda u: u.is_staff, login_url=reverse_lazy('logout_user'))
@login_required(login_url='/register/login_user')
def accounts(request):
    users = list(User.objects.all())
    return render(request, 'payapp/accounts.html', {'users': users})


@user_passes_test(lambda u: u.is_staff, login_url=reverse_lazy('logout_user'))
@login_required(login_url='/register/login_user')
def transactions(request):
    transaction_history = list(Transaction.objects.filter(request=False).order_by('-modified'))
    return render(request, 'payapp/transactions.html', {'transaction_history': transaction_history})