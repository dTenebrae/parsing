### Курсовая работа по курсу парсинга GB ###

***

>Источник - Instagram.com  
>
>На вход программе подается 2 имени пользователя.
Задача программы найти самую короткую цепочку рукопожатий между этими пользователями.
Рукопожатием считаем только взаимоподписанных пользователей

Результат работы скрипта на пользователях dtenebrae и gizmothenudist можно видеть ниже.   

Node('/dtenebrae')  
├── Node('/dtenebrae/gurkin_ivan_murom')  
├── Node('/dtenebrae/antonovre82')  
├── Node('/dtenebrae/fredandmorty')  
&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;├── Node('/dtenebrae/fredandmorty/gizmothenudist')   
&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;...  

├── Node('/dtenebrae/rudakov_alexandrr')  
├── Node('/dtenebrae/nevinnayaeda')  
├── Node('/dtenebrae/dmitriymypom')  
├── Node('/dtenebrae/moumou_taro')  
...  
└── Node('/dtenebrae/andyponk1')

Количество пользователей в очереди: 114  

Количество переходов между пользователями dtenebrae и gizmothenudist: 2  
Путь:  
gizmothenudist -> fredandmorty -> dtenebrae


