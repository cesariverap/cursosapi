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

@app.route('/api/cursos/info_from_url', methods=['GET'])
def get_course_info_from_url():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Falta el parámetro URL'}), 400

    try:
        response = requests.get(url)
        if response.status_code != 200:
            return jsonify({'error': 'No se pudo acceder a la URL proporcionada'}), 500

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract course title
        title = soup.find('h1', class_='text-4xl').get_text(strip=True) if soup.find('h1', class_='text-4xl') else 'No title found'
        
        # Extract instructor (author)
        instructor = soup.select_one('a.font-medium.text-gray-500').get_text(strip=True) if soup.select_one('a.font-medium.text-gray-500') else 'No instructor found'
        
        # Extract image URL from the specific section you mentioned
        image_element = soup.select_one('a.relative.block.group img')
        image_url = image_element['src'] if image_element else 'No image found'
        
        # Extract price information
        current_price = soup.select_one('div.inline-flex.text-sm.font-medium.text-red-600 span').get_text(strip=True) if soup.select_one('div.inline-flex.text-sm.font-medium.text-red-600 span') else 'Free'
        original_price = soup.select_one('div.inline-flex.text-sm.font-medium.text-slate-500').get_text(strip=True) if soup.select_one('div.inline-flex.text-sm.font-medium.text-slate-500') else ''
        
        # Extract rating and reviews
        rating = soup.select_one('span.font-semibold.text-gray-900').get_text(strip=True) if soup.select_one('span.font-semibold.text-gray-900') else '0.0'
        reviews = soup.select_one('span.inline-block.text-gray-500').get_text(strip=True).strip('()') if soup.select_one('span.inline-block.text-gray-500') else '0'
        
        # Extract coupon code if available
        coupon_element = soup.select_one('span.text-red-600.dark\\:text-red-400.font-bold')
        coupon = coupon_element.get_text(strip=True) if coupon_element else ''
        
        # Extract publication date
        date_published = soup.select_one('p.text-center.text-sm.text-gray-600').get_text(strip=True).replace('Publicado el', '').strip() if soup.select_one('p.text-center.text-sm.text-gray-600') else ''
        
        # Extract category
        category = soup.select_one('a.inline-flex.items-center.px-3.py-2.bg-gray-700').get_text(strip=True) if soup.select_one('a.inline-flex.items-center.px-3.py-2.bg-gray-700') else ''

        # Extract "Lo que aprenderás" section
        learning_items = []
        learning_section = soup.find('h2', string='Lo que aprenderás')
        if learning_section:
            learning_list = learning_section.find_next('ul')
            if learning_list:
                learning_items = [li.get_text(strip=True) for li in learning_list.find_all('li')]

        # Extract "Requisitos" section
        requirements = []
        requirements_section = soup.find('h2', string='Requisitos')
        if requirements_section:
            requirements_list = requirements_section.find_next('ul')
            if requirements_list:
                requirements = [li.get_text(strip=True) for li in requirements_list.find_all('li')]

        # Extract "Descripción" section
        description = ''
        description_section = soup.find('h2', string='Descripción')
        if description_section:
            description_div = description_section.find_next('div')
            if description_div:
                # Get all paragraphs and join them with newlines
                description = '\n\n'.join(p.get_text(strip=True) for p in description_div.find_all('p'))

        # Extract "¿Para quién es este curso?" section
        target_audience = []
        audience_section = soup.find('h2', string='¿Para quién es este curso?')
        if audience_section:
            audience_list = audience_section.find_next('ul')
            if audience_list:
                target_audience = [li.get_text(strip=True) for li in audience_list.find_all('li')]

        scraped_at = datetime.utcnow().isoformat()

        return jsonify({
            'curso': {
                'title': title,
                'instructor': instructor,
                'image_url': image_url,
                'current_price': current_price,
                'original_price': original_price,
                'coupon': coupon,
                'rating': rating,
                'reviews': reviews,
                'category': category,
                'date_published': date_published,
                'link': url,
                'scraped_at': scraped_at,
                'learning_outcomes': learning_items,
                'requirements': requirements,
                'description': description,
                'target_audience': target_audience
            }
        })

    except Exception as e:
        app.logger.error(f"Error scraping: {str(e)}")
        return jsonify({'error': 'Ocurrió un error procesando la página', 'details': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)