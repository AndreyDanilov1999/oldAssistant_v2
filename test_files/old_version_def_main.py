@profile
def main():
    speak("Привет")
    for text in get_audio():
        if 'перси' in text:
            if 'видео' in text:
                open_video()
            elif "поищи" in text or 'найди' in text:
                query = text.replace("поищи", "").replace("найди", "").replace("перси", "").strip()
                speak(f"Сейчас найду {query}")
                search_yandex(query)
            elif 'проверь' in text:
                speak(random.choice(lists.Approval))
                add_function()
            elif 'повтори' in text:
                query = text.replace("повтор", "").replace("перси", "").strip()
                speak(f"Конечно! {query}")
            elif 'выключи комп' in text:
                shutdown_windows()
            elif 'запус' in text or 'откр' in text or 'вкл' in text:
                if 'калькулятор' in text:
                    open_calc()
                elif 'раст' in text:
                    open_Rust_exe()
                elif 'фактор' in text or 'завод' in text:
                    open_FactoryGame_exe()
                elif 'пар' in text: #parsec
                    open_parsecd_exe()
                elif 'пайтон' in text or 'питон' in text:
                    open_pycharm64_exe()
                elif 'дис' in text:
                    open_Discord_exe()
                elif 'браузер' in text:
                    open_browser_exe()
                elif 'саун' in text:
                    open_Soundpad_exe()
                elif 'тер' in text:
                    open_Terraria_exe()
                elif 'таймер' in text:
                    open_timer_exe()
                elif 'майн' in text:
                    open_Minecraft()
                elif 'фотошоп' in text:
                    open_Photoshop_exe()
                elif 'вегас' in text:
                    open_vegas_exe()
                elif 'грин хе' in text:
                    open_Green_Hell()
                elif 'рафт' in text:
                    open_Raft()
                elif 'рдр' in text:
                    open_Red_Dead_Redemption_2()
                elif 'сиф' in text:
                    open_Sifu_exe()
                elif 'контр' in text or 'кантр' in text:
                    open_Control_exe()
                elif 'марв' in text or 'райв' in text:
                    open_MarvelRivals_exe()
                else:
                    speak(random.choice(lists.What))
            elif 'закрой' in text or 'выкл' in text:
                if 'раст' in text:
                    close_Rust_exe()
                elif 'фактор' in text or 'завод' in text:
                    close_FactoryGame_exe()
                elif 'пар' in text: #parsec
                    close_parsecd_exe()
                elif 'пайтон' in text or 'питон' in text:
                    close_pycharm64_exe()
                elif 'дис' in text:
                    close_Discord_exe()
                elif 'браузер' in text:
                    close_browser_exe()
                elif 'саун' in text:
                    close_Soundpad_exe()
                elif 'калькулятор' in text:
                    close_calc()
                elif 'тер' in text:
                    close_Terraria_exe()
                elif 'таймер' in text:
                    close_timer_exe()
                elif 'майн' in text:
                    close_Minecraft()
                elif 'фотошоп' in text:
                    close_Photoshop_exe()
                elif 'вегас' in text:
                    close_vegas_exe()
                elif 'грин хе' in text:
                    close_Green_Hell()
                elif 'рафт' in text:
                    close_Raft()
                elif 'рдр' in text:
                    close_Red_Dead_Redemption_2()
                elif 'сиф' in text:
                    close_Sifu_exe()
                elif 'контр' in text or 'кантр' in text:
                    close_Control_exe()
                elif 'марв' in text or 'райв' in text:
                    close_MarvelRivals_exe()
                else:
                    speak(random.choice(lists.What))
            elif "пауз" in text or "вруб" in text:
                controller.play_pause()
                speak(random.choice(lists.Approval))
            elif "след" in text:
                controller.next_track()
                speak(random.choice(lists.Approval))
            elif "пред" in text:
                controller.previous_track()
                speak(random.choice(lists.Approval))
            else:
                speak(random.choice(lists.Greet))

        elif "перезагрузка ассистент" in text:
            restart_system()
            break
    gc.collect()