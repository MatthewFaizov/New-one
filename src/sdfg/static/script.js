// Этот файл подключён на всех страницах.
// Каждый блок срабатывает только если на странице есть нужная форма.

// Показать сообщение под формой (красное — ошибка, зелёное — успех)
function showMessage(text, isError) {
    $('#message')
        .text(text)
        .removeClass('error ok')
        .addClass(isError ? 'error' : 'ok');
}

// Отправить данные на сервер в формате JSON
function postJSON(url, data) {
    return $.ajax({
        url: url,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data)
    });
}

$(document).ready(function () {

    // ---------- Регистрация ----------
    $('#register-form').on('submit', function (e) {
        e.preventDefault(); // не перезагружать страницу

        if ($('#password').val() !== $('#confirm_password').val()) {
            showMessage('Пароли не совпадают', true);
            return;
        }

        postJSON('/user_register', {
            first_name: $('#first_name').val(),
            last_name: $('#last_name').val(),
            email: $('#email').val(),
            password: $('#password').val()
        }).done(function (res) {
            if (res.result) {
                window.location.href = '/lk';
            } else {
                showMessage(res.error, true);
            }
        }).fail(function () {
            showMessage('Сервер не отвечает', true);
        });
    });

    // ---------- Вход ----------
    $('#login-form').on('submit', function (e) {
        e.preventDefault();

        postJSON('/user_login', {
            email: $('#email').val(),
            password: $('#password').val()
        }).done(function (res) {
            if (res.result) {
                window.location.href = '/lk';
            } else {
                showMessage(res.error, true);
            }
        }).fail(function () {
            showMessage('Сервер не отвечает', true);
        });
    });

    // ---------- Новая транзакция ----------
    $('#transaction-form').on('submit', function (e) {
        e.preventDefault();

        postJSON('/add_transaction', {
            type: $('#type').val(),
            amount: $('#amount').val(),
            description: $('#description').val()
        }).done(function (res) {
            if (res.result) {
                window.location.reload(); // обновить баланс и список
            } else {
                showMessage(res.error, true);
            }
        }).fail(function () {
            showMessage('Сервер не отвечает', true);
        });
    });

    // ---------- Запрос в нейросеть ----------
    $('#ai-form').on('submit', function (e) {
        e.preventDefault();

        var button = $('#ai-button');
        button.prop('disabled', true).text('Нейросеть думает...');
        showMessage('', false);
        $('#ai-answer').prop('hidden', true);

        postJSON('/ask_ai', {
            question: $('#question').val()
        }).done(function (res) {
            if (res.result) {
                // .text(), а не .html(), чтобы ответ не мог вставить на страницу свой код
                $('#ai-answer').text(res.answer).prop('hidden', false);
            } else {
                showMessage(res.error, true);
            }
        }).fail(function () {
            showMessage('Сервер не отвечает', true);
        }).always(function () {
            button.prop('disabled', false).text('Отправить запрос в нейросеть');
        });
    });
});
