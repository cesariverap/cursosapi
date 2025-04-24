from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

app = Flask(__name__)

BASE_URL = "https://www.cursosdev.com/coupons/Spanish"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9'
}

def scrape_course(card):
    try:
        # Extraer enlace completo
        a_tag = card.find('a', href=True)
        full_link = a_tag['href']

        # Extraer título
        title = card.find('h2').text.strip()

        # Extraer precios
        price_divs = card.select('div.flex.items-center.justify-between.space-x-2 div.flex.items-center.space-x-2')
        current_price = price_divs[0].find_all('div')[0].text.strip()
        original_price = price_divs[0].find_all('div')[1].text.strip()

        # Extraer descuento
        discount_tag = card.select_one('div.bg-green-600, div.bg-green-500')
        discount = discount_tag.text.strip() if discount_tag else 'No disponible'

        # Extraer rating
        rating = card.select_one('span.font-semibold').text.strip()

        # Extraer instructor
        instructor = card.find('i').text.strip()

        # Extraer imagen
        image_tag = card.find('img', class_='absolute')
        full_image_url = image_tag['src']

        return {
            'title': title,
            'link': full_link,
            'current_price': current_price,
            'original_price': original_price,
            'discount': discount,
            'rating': rating,
            'instructor': instructor,
            'image_url': full_image_url,
            'scraped_at': datetime.now().isoformat()
        }
    except Exception as e:
        app.logger.error(f"Error procesando curso: {str(e)}")
        return None

@app.route('/api/cursos', methods=['GET'])
def get_cursos():
    """Endpoint principal para obtener cursos por página"""
    try:
        page = request.args.get('page', default=1, type=int)
        if page < 1:
            return jsonify({'error': 'El número de página debe ser mayor o igual a 1'}), 400
        
        url = f"{BASE_URL}?page={page}" if page > 1 else BASE_URL
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            course_cards = soup.find_all('div', class_='transition-transform')
            
            cursos = []
            for card in course_cards:
                curso = scrape_course(card)
                if curso:
                    cursos.append(curso)
            
            if not cursos:
                return jsonify({'message': 'No se encontraron cursos en esta página', 'page': page}), 404
            
            return jsonify({
                'page': page,
                'total_cursos': len(cursos),
                'cursos': cursos,
                'next_page': page + 1 if len(cursos) > 0 else None
            })
        else:
            return jsonify({'error': f'Error al acceder a la página. Código: {response.status_code}'}), 500
            
    except Exception as e:
        app.logger.error(f"Error en la API: {str(e)}")
        return jsonify({'error': 'Ocurrió un error interno en el servidor'}), 500

@app.route('/api/cursos/total_pages', methods=['GET'])
def get_total_pages():
    """Endpoint para obtener el número total de páginas disponibles"""
    try:
        response = requests.get(BASE_URL, headers=HEADERS)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar todos los enlaces que parecen ser paginación
            page_links = soup.select('nav a[href*="page="]')
            
            if page_links:
                # Extraer los números de página y obtener el máximo
                page_numbers = []
                for link in page_links:
                    href = link.get('href')
                    if 'page=' in href:
                        try:
                            page_num = int(href.split('page=')[-1])
                            page_numbers.append(page_num)
                        except ValueError:
                            continue
                
                if page_numbers:
                    return jsonify({'total_pages': max(page_numbers)})

        return jsonify({'total_pages': 1})
    
    except Exception as e:
        app.logger.error(f"Error obteniendo total de páginas: {str(e)}")
        return jsonify({'error': 'No se pudo determinar el total de páginas'}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)