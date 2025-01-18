from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import time
from pymongo import MongoClient
from bs4 import BeautifulSoup

data = 'Tomorrow'  # Задайте нужную вам дату
coefficient = list(range(27, 30))  # Список от 27 до 29 (30 не включается)

countries = ['india']

client = MongoClient('mongodb://localhost:27017/')
db = client['fonbet']
collection = db['games']

def init_webdriver():
    driver = webdriver.Chrome()
    stealth(driver,
            languages=['en-US', 'en'],
            vendor='Google Inc',
            platform='Win32',
            webgl_vendor='Intel Inc',
            renderer='Intel Iris OpenGL Engine'
            )
    return driver

def parser_country_page(url, country, driver, results):
    driver.get(url)
    time.sleep(5)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    players_and_links = soup.find_all('a', class_='table-component-text--Tjj3g sport-event__name--YAs00 _clickable--xICGO _event-view--nrsM2 _compact--MZ0VP')

    for element in players_and_links:
        player_text = element.get_text(strip=True)
        href = element.get('href')

        # Находим дату события
        date_element = element.find_next('span', class_='event-block-planned-time__time--RtMgQ')
        if date_element:
            event_date = date_element.get_text(strip=True)
        else:
            event_date = None

        # Проверяем, если дата совпадает с переменной data
        if event_date and data in event_date:
            if href:
                # Если ссылка относительная, то делаем ее абсолютной
                if not href.startswith('https://'):
                    shortened_href = 'https://fon.bet' + href
                else:
                    shortened_href = href
                result = f'Player/Event: {player_text}, Link: {shortened_href}, Date: {event_date}'
            else:
                result = f'Player/Event: {player_text}, No link found, Date: {event_date}'
            
            # Добавляем результат в список
            results.append({
                'player': player_text,
                'link': shortened_href,
                'date': event_date
            })

def country_page(driver, results):
    for country in countries:
        url = f'https://fon.bet/sports/football/{country}'
        print(f'Parsing {url}...')
        parser_country_page(url, country, driver, results)  # Парсим каждую страну с использованием Selenium

def check_coefficient(driver, results):
    valid_coefficients = set()  # Используем set для уникальных коэффициентов

    for result in results:
        link = result['link']
        print(f'Opening link: {link}')
        driver.get(link)
        time.sleep(3)  # Подождем, пока страница загрузится

        for n in range(6):  # Перебор всех значений от 0 до 5 для переменной n
            for m in range(6):
                # Находим коэффициенты на странице
                coefficients_elements = driver.find_elements(By.CLASS_NAME, 'value--v77pD._center--RlTqx')  # Пример для нахождения коэффициента
                
                # Проверяем, что список не пуст
                if coefficients_elements:
                    # Извлекаем последний коэффициент
                    last_coefficient_element = coefficients_elements[-1]
                    coefficient_text = last_coefficient_element.text.strip()
                    print(f"Last coefficient: {coefficient_text}")

                    try:
                        coefficient_value = float(coefficient_text)
                        if coefficient_value in coefficient:
                            valid_coefficients.add(coefficient_value)  # Добавляем в set, чтобы избежать дублирования
                            print(f"Found coefficient {coefficient_value} in the range {coefficient}. Added to list.")

                            # Добавляем данные в MongoDB
                            score_elements = driver.find_elements(By.CLASS_NAME, 'score-wrap--yW40V')
                            score_text = ''.join([s.text for s in score_elements]).replace('\u00A0', '')

                            if score_text:
                                score = score_text.strip()
                                event_data = {
                                    'player': result['player'],
                                    'date': result['date'],
                                    'coefficient': coefficient_value,
                                    'score': score
                                }
                                collection.insert_one(event_data)
                                print(f"Saved event to MongoDB: {event_data}")
                        else:
                            print(f"Coefficient {coefficient_value} not in the specified range. Skipped.")
                    except ValueError:
                        print(f"Invalid coefficient value: {coefficient_text}")
                else:
                    print("No coefficients found on this page.")

                # Try to find the score and convert to integers if valid
                score = driver.find_elements(By.CLASS_NAME, 'score-wrap--yW40V')
                
                # Join the text of all score elements in the list
                score_text = ''.join([s.text for s in score]).replace('\u00A0', '')

                if score_text:
                    try:
                        first_char = int(score_text[0])
                        last_char = int(score_text[-1])

                        print(f"Score: {first_char}  {last_char}")

                        # Find the buttons
                        buttons_one_plus = driver.find_elements(By.XPATH, '/html/body/application/div[2]/div[1]/div/div/div/div[2]/div/div/div[1]/div/div/div/div/div/div[1]/div/div[1]/div[3]/div[8]/div[2]/div/div/div[2]/div/div/div[1]/div[2]/span[2]')
                        buttons_two_plus = driver.find_elements(By.XPATH, '/html/body/application/div[2]/div[1]/div/div/div/div[2]/div/div/div[1]/div/div/div/div/div/div[1]/div/div[1]/div[3]/div[8]/div[2]/div/div/div[2]/div/div/div[3]/div[2]/span[2]')
                        buttons_one_minus = driver.find_elements(By.XPATH, '/html/body/application/div[2]/div[1]/div/div/div/div[2]/div/div/div[1]/div/div/div/div/div/div[1]/div/div[1]/div[3]/div[8]/div[2]/div/div/div[2]/div/div/div[1]/div[2]/span[1]')
                        buttons_two_minus = driver.find_elements(By.XPATH, '/html/body/application/div[2]/div[1]/div/div/div/div[2]/div/div/div[1]/div/div/div/div/div/div[1]/div/div[1]/div[3]/div[8]/div[2]/div/div/div[2]/div/div/div[3]/div[2]/span[1]')

                        # Perform the button click actions based on conditions
                        if first_char < n and buttons_one_plus:
                            buttons_one_plus[0].click()
                        elif last_char < m and buttons_two_plus:
                            buttons_two_plus[0].click()
                        elif first_char > n and buttons_one_minus:
                            buttons_one_minus[0].click()
                        elif last_char > m and buttons_two_minus:
                            buttons_two_minus[0].click()
                    except ValueError:
                        print(f"Invalid score format: {score_text}")
                else:
                    print("No score found on this page.")

            print("\nValid coefficients found:", valid_coefficients)

if __name__ == '__main__':
    driver = init_webdriver()
    
    results = []  # Список для хранения результатов
    country_page(driver, results)
    
    check_coefficient(driver, results)  # Вызываем функцию для проверки коэффициентов
    
    driver.quit()
