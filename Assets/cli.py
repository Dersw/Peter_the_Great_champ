def select_speaker():
    speakers = {
        "1": ("aidar", "aidar (Мужской)"),
        "2": ("baya", "baya (Женский)"),
        "3": ("kseniya", "kseniya (Женский, четкий)"),
        "4": ("xenia", "xenia (Женский, мягкий)")
    }

    print("ВЫБОР ГОЛОСА СИНТЕЗАТОРА")
    for key, (code, name) in speakers.items():
        print(f"  [{key}] {name}")

    while True:
        choice = input("Введите номер или название голоса: ").strip().lower()
        
        if choice in speakers:
            return speakers[choice][0]
            
        for code, name in speakers.values():
            if choice == code or choice in name.lower():
                return code
                
        print("Неверный ввод")