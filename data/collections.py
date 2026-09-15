"""Коллекция компонентов ПК (power_components).

Статусы:
    опубликован — отображается в каталоге (плитка) и в ленте
    черновик    — отображается только на странице добавления, ровно одна запись
    удален      — логическое удаление, в интерфейсе не отображается
"""

power_components = [
    {
        "id": 1,
        "title": "Intel Core i5-13600K",
        "power_watt": 125,
        "weight_gram": 55,
        "description": (
            "14 ядер, разгоняемый, лучший баланс цены и производительности "
            "для игровой сборки. Требует хорошего охлаждения при работе под нагрузкой."
        ),
        "status": "опубликован",
        "image_url": "http://localhost:9000/power-components/cpu-i5-13600k.jpg",
        "video_url": "http://localhost:9000/power-components/cpu-i5-13600k.mp4",
        "likes": [3, 7, 12],
    },
    {
        "id": 2,
        "title": "NVIDIA RTX 4070",
        "power_watt": 200,
        "weight_gram": 1050,
        "description": (
            "Оптимальная видеокарта для разрешения 1440p, поддержка DLSS 3, "
            "тихая работа под нагрузкой и умеренное энергопотребление."
        ),
        "status": "опубликован",
        "image_url": "http://localhost:9000/power-components/gpu-rtx-4070.jpg",
        "video_url": "http://localhost:9000/power-components/gpu-rtx-4070.mp4",
        "likes": [1, 4, 9, 15],
    },
    {
        "id": 3,
        "title": "AMD Ryzen 7 7800X3D",
        "power_watt": 120,
        "weight_gram": 50,
        "description": (
            "Лидер по игровой производительности благодаря технологии 3D V-Cache, "
            "невысокий нагрев и низкое энергопотребление для своего класса."
        ),
        "status": "опубликован",
        "image_url": "http://localhost:9000/power-components/cpu-7800x3d.jpg",
        "video_url": "http://localhost:9000/power-components/cpu-7800x3d.mp4",
        "likes": [2, 5, 9, 11, 14, 18, 21],
    },
    {
        "id": 4,
        "title": "RTX 4080 Super",
        "power_watt": 320,
        "weight_gram": 2050,
        "description": (
            "Производительная видеокарта для разрешения 4K. Требует мощного блока "
            "питания и хорошей продувки корпуса."
        ),
        "status": "опубликован",
        "image_url": "http://localhost:9000/power-components/gpu-4080-super.jpg",
        "video_url": "http://localhost:9000/power-components/gpu-4080-super.mp4",
        "likes": [1, 6, 13, 17, 20],
    },
    {
        "id": 5,
        "title": "ASUS TUF Gaming RTX 4080",
        "power_watt": 320,
        "weight_gram": 2380,
        "description": (
            "Надёжная и холодная видеокарта с металлическим кожухом и вентиляторами "
            "повышенной прочности. Усиленная система охлаждения снижает шум."
        ),
        "status": "опубликован",
        "image_url": "http://localhost:9000/power-components/gpu-asus-tuf-4080.jpg",
        "video_url": "http://localhost:9000/power-components/gpu-asus-tuf-4080.mp4",
        "likes": [4, 8, 10, 16, 19],
    },
    {
        "id": 6,
        "title": "NVIDIA GeForce RTX 4090",
        "power_watt": 450,
        "weight_gram": 2186,
        "description": (
            "Флагманская видеокарта на архитектуре Ada Lovelace, 24 ГБ GDDR6X, "
            "максимальная производительность для игр и рендеринга."
        ),
        "status": "черновик",
        "image_url": "http://localhost:9000/power-components/gpu-4090.jpg",
        "video_url": "http://localhost:9000/power-components/gpu-4090.mp4",
        "likes": [],
    },
    {
        "id": 7,
        "title": "Intel Core i9-13900",
        "power_watt": 253,
        "weight_gram": 60,
        "description": "Позиция снята с продажи.",
        "status": "удален",
        "image_url": "http://localhost:9000/power-components/cpu-i9-13900.jpg",
        "video_url": "http://localhost:9000/power-components/cpu-i9-13900.mp4",
        "likes": [8],
    },
]
