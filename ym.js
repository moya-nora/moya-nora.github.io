/* Яндекс Метрика: сколько людей открывают Нору и что нажимают. Без Вебвизора — записи экрана нет */
(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};m[i].l=1*new Date();
for(var j=0;j<document.scripts.length;j++){if(document.scripts[j].src===r){return;}}
k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})(window,document,'script','https://mc.yandex.ru/metrika/tag.js?id=114237349','ym');
ym(114237349,'init',{ssr:true,clickmap:true,referrer:document.referrer,url:location.href,accurateTrackBounce:true,trackLinks:true});
/* свои заходы владельца помечаем, чтобы в Метрике смотреть только чужих: Telegram-аккаунт владельца, ссылка с ?me=1 или уже отмеченный браузер */
(function(){try{var d=decodeURIComponent(decodeURIComponent(location.hash+location.search)),ls=localStorage;
if(/"id":648225353\b/.test(d)||/[?&]me=1\b/.test(location.search))ls.setItem('zal.owner','1');
if(/[?&]me=0\b/.test(location.search))ls.removeItem('zal.owner');
var o=ls.getItem('zal.owner')?'да':'нет';ym(114237349,'params',{'Владелец':o});ym(114237349,'userParams',{'Владелец':o})}catch(e){}})();
