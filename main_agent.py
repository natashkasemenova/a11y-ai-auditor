import sqlite3
import json  
import os    
import time

# Імпортуємо ChatOllama
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate

# 1. ініціалізація локальної моделі
llm = ChatOllama(
    model="llama3",
    temperature=0.2  # робимо відповіді точними та технічними
)

# 2. функція для витягування даних з бази знань
def get_dstu_context(lighthouse_id):
    try:
        conn = sqlite3.connect('standards.db')
        cursor = conn.cursor()
        # шукаємо норму ДСТУ за ідентифікатором помилки з Lighthouse
        query = """
        SELECT d.clause, d.requirement 
        FROM dstu_standards d
        JOIN audit_mapping m ON d.id = m.standard_id
        WHERE m.lighthouse_id = ?
        """
        cursor.execute(query, (lighthouse_id,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            return f"Пункт ДСТУ {res[0]}: {res[1]}"
        return "Відповідну норму ДСТУ не знайдено."
    except Exception as e:
        return f"Помилка бази даних!: {e}"

# 3. налаштування промпту для агента
template = """
Ти — професійний консультант з веб-доступності (WCAG/ДСТУ).
Твоє завдання: проаналізувати помилку аудиту на основі закону.

КОНТЕКСТ (Вимога ДСТУ): {context}
ПОМИЛКА: {error_id}
ТЕХНІЧНІ ДЕТАЛІ: {tech_info}

Напиши українською мовою:
1. Пояснення, чому це важливо згідно з ДСТУ.
2. Конкретну пораду розробнику (приклад коду HTML/CSS).
"""

prompt = PromptTemplate.from_template(template)

# 4. основна логіка запуску апробації
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, 'report.json')

    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        audits = data.get('audits', {})
        
        # --- ЕТАП 1: ЗАГАЛЬНА СТАТИСТИКА ЗВІТУ ---
        all_critical_errors = [aid for aid, val in audits.items() if val.get('score') == 0]
        
        print(f"\n" + "="*60)
        print(f"ЗВІТ LIGHTHOUSE: {report_path}")
        print(f"Загальна кількість знайдених критичних помилок: {len(all_critical_errors)}")
        print("="*60)
        
        # виводимо повний список ідентифікаторів для прозорості
        print("Список усіх технічних ідентифікаторів помилок:")
        for aid in all_critical_errors:
            print(f"  • {aid}")
        print("-" * 60)

        # --- ЕТАП 2: ФІЛЬТРАЦІЯ ТА ІНТЕЛЕКТУАЛЬНИЙ АНАЛІЗ ---
        # ті, що ми можемо проаналізувати за нашою базою даних 
        target_ids = ['image-alt', 'color-contrast', 'link-name', 'html-has-lang', 'button-name', 'label']
        errors_to_process = [aid for aid in all_critical_errors if aid in target_ids]
        
        total_for_ai = len(errors_to_process)
        
        print(f"ОБРАНО ДЛЯ АНАЛІЗУ (наявні у базі даних проекту): {total_for_ai}")
        print("="*60)

        # Засікаємо загальний час старту роботи ШІ для всього сайту
        total_start_time = time.time()
        
        for index, error_id in enumerate(errors_to_process, 1):
            print(f"\n[АНАЛІЗ ПОМИЛКИ {index} з {total_for_ai}]: {error_id.upper()}")
            
            # підготовка контексту
            context = get_dstu_context(error_id)
            audit_data = audits.get(error_id)
            tech_info = audit_data.get('description', 'Деталі відсутні')

            final_prompt = prompt.format(
                context=context, 
                error_id=error_id, 
                tech_info=tech_info
            )

            try:
                # ВСТАВЛЯЄМО ТАЙМЕР ТУТ: засікаємо час безпосередньо перед викликом Llama 3
                error_start_time = time.time()

                # виклик моделі Llama 3
                response = llm.invoke(final_prompt)

                # засікаємо час одразу після того, як модель закінчила генерацію
                error_end_time = time.time()
                error_execution_time = error_end_time - error_start_time
                
                # виклик моделі Llama 3
                response = llm.invoke(final_prompt)
                print(f"\nРЕКОМЕНДАЦІЯ АГЕНТА:")
                print(response.content)
                print("-" * 40)
                # Виводимо точний час обробки конкретно цієї помилки у секундах
                print(f"Час обробки помилки {error_id}: {error_execution_time:.2f} сек.")
                print("-" * 40)
            except Exception as e:
                print(f"Помилка при аналізі {error_id}: {e}")
                
        # Рахуємо загальний час, який знадобився на весь аудит сайту
        total_end_time = time.time()
        total_execution_time = total_end_time - total_start_time
        
        print(f"\n" + "="*60)
        print(f"ПРОЦЕС АПРОБАЦІЇ ЗАВЕРШЕНО")
        print("="*60)
        print(f"Загальний час роботи штучного інтелекту: {total_execution_time:.2f} секунд.")
        print("="*60)
        
    else:
        print(f"Файл {report_path} не знайдено.")