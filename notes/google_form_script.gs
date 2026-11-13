function createNoraForm() {
  var f = FormApp.create('Нора — что скажешь?');
  f.setDescription('Спасибо, что помогаешь! 15–20 минут: сначала попробуй задания в приложении, потом ответь на вопросы. Честная критика полезнее похвалы.\n\nОткрыть Нору: @Wonderbookworld_bot в Telegram → «Открыть Нору».');
  f.setCollectEmail(false); f.setProgressBar(true);
  f.addTextItem().setTitle('Как тебя зовут?').setRequired(true);
  f.addPageBreakItem().setTitle('Задания в приложении').setHelpText('Отметь, что получилось сделать.');
  f.addCheckboxItem().setTitle('Что получилось?').setChoiceValues([
    'Зарегистрироваться и пройти знакомство','Полистать «Шуршуня советует» и открыть книгу','Добавить 3 книги в «Хочу прочитать»',
    'Отметить 3 книги «Прочитано» и поставить оценку','Полистать «Ленту»: лайкнуть и пропустить по 5 книг','Найти книгу по названию или автору',
    'Написать в поиск просьбу своими словами (например, «что почитать в отпуске»)','Попробовать фильтры в поиске','Нажать «Где прочитать?» и перейти в магазин',
    'Поставить цель на год в «Статистике»','Добавить друга','Переслать книгу другу','Убрать книгу с полки','Закрыть и открыть Нору — полки на месте']);
  f.addParagraphTextItem().setTitle('Что не получилось и почему?');
  f.addPageBreakItem().setTitle('Короткие вопросы').setHelpText('1 — совсем нет, 5 — очень.');
  f.addMultipleChoiceItem().setTitle('Сколько книг ты читаешь в год?').setChoiceValues(['0–5','6–20','больше 20']);
  f.addCheckboxItem().setTitle('Где обычно ищешь, что почитать?').setChoiceValues(['советуют друзья','соцсети, блогеры','ЛитРес, Яндекс Книги','книжные магазины']).showOtherOption(true);
  var sc = function(t){ f.addScaleItem().setTitle(t).setBounds(1,5).setLabels('совсем нет','очень'); };
  sc('Сразу понятно, зачем это приложение?');
  f.addMultipleChoiceItem().setTitle('Регистрация и знакомство прошли легко?').setChoiceValues(['да','нет']);
  sc('Книги в «Шуршуня советует» подходят твоему вкусу?');
  f.addMultipleChoiceItem().setTitle('Нашла хотя бы одну книгу, которую хочешь прочитать?').setChoiceValues(['да','нет']);
  sc('Лента удобна и понятна?');
  sc('Поиск находит то, что ты ищешь?');
  f.addMultipleChoiceItem().setTitle('Поиск понял просьбу своими словами?').setChoiceValues(['да','частично','нет','не пробовала']);
  f.addMultipleChoiceItem().setTitle('Понятно, как добавить и убрать книгу с полки?').setChoiceValues(['да','нет']);
  f.addMultipleChoiceItem().setTitle('Обложки и описания книг правильные?').setChoiceValues(['да','были ошибки']);
  f.addMultipleChoiceItem().setTitle('Кнопка «Где прочитать?» пригодилась?').setChoiceValues(['да','нет','не нажимала']);
  sc('Статистика и цель на год интересны?');
  sc('Нравится, как выглядит приложение?');
  f.addMultipleChoiceItem().setTitle('Всё работало быстро?').setChoiceValues(['да','иногда тормозило','нет']);
  f.addMultipleChoiceItem().setTitle('С какого устройства заходила?').setChoiceValues(['iPhone','Android','компьютер']);
  f.addPageBreakItem().setTitle('Своими словами').setHelpText('Можно коротко, хоть одним словом.');
  ['Как бы ты объяснила подруге в двух словах, что такое Нора?','Что понравилось больше всего?','Что раздражало или казалось лишним?',
   'В какой момент ты застряла или не поняла, что делать дальше?','Какая книга из советов попала в точку? А какая совсем мимо и почему?',
   'Что ты написала в поиск своими словами и что получила?','Чего не хватило? Какую функцию ты бы добавила?',
   'Чем ты сейчас пользуешься для книг и чем Нора лучше или хуже?','Встретила ошибки? Опиши, что и где (скриншот можно прислать в бота @Wonderbookworld_bot)',
   'Если бы можно было поменять одну вещь — что бы это было?'].forEach(function(t){ f.addParagraphTextItem().setTitle(t); });
  f.addPageBreakItem().setTitle('В конце');
  f.addMultipleChoiceItem().setTitle('Будешь пользоваться Норой дальше?').setChoiceValues(['да','может быть','нет']);
  f.addScaleItem().setTitle('Насколько вероятно, что ты посоветуешь Нору друзьям?').setBounds(0,10).setLabels('точно нет','точно да');
  f.addMultipleChoiceItem().setTitle('Хочешь получать книжные советы в Telegram раз в неделю?').setChoiceValues(['да','нет']);
  f.addMultipleChoiceItem().setTitle('Заполняла бы читательский дневник после книги, если это 30 секунд нажатий?').setChoiceValues(['да','нет','может быть']);
  f.addParagraphTextItem().setTitle('Что заставило бы тебя открывать Нору каждую неделю?');
  f.setConfirmationMessage('Спасибо! Шуршуня передаёт привет 🦔');
  Logger.log('ССЫЛКА ДЛЯ ДРУЗЕЙ: ' + f.getPublishedUrl());
  Logger.log('РЕДАКТИРОВАТЬ: ' + f.getEditUrl());
}
