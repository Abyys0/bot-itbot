from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# URL da API interna do bot
BOT_API_URL = "http://127.0.0.1:5001/api/bot"

# Funções para comunicar com a API do bot
def call_bot_api(endpoint, method='GET', data=None):
    """Chama a API interna do bot"""
    try:
        url = f"{BOT_API_URL}{endpoint}"
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        else:
            return {'success': False, 'error': 'Método não suportado'}
        
        return response.json()
    except requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Bot não está online ou API indisponível'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Timeout na comunicação com o bot'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Funções para gerenciar tickets localmente (fallback)
def load_tickets():
    """Carrega tickets do arquivo JSON"""
    try:
        if os.path.exists('tickets.json'):
            with open('tickets.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception:
        return []

# Funções para gerenciar contas
def load_accounts():
    """Carrega contas do arquivo JSON"""
    try:
        if os.path.exists('accounts.json'):
            with open('accounts.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def save_accounts(accounts):
    """Salva contas no arquivo JSON"""
    try:
        with open('accounts.json', 'w', encoding='utf-8') as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def get_all_tickets():
    """Retorna todos os tickets (tenta API primeiro, depois fallback)"""
    # Tenta buscar via API do bot
    result = call_bot_api('/tickets')
    if result.get('success'):
        return result.get('tickets', [])
    
    # Fallback para arquivo local
    return load_tickets()

# ==================== ENDPOINTS ====================

@app.route('/api/health', methods=['GET'])
def health():
    """Verifica se a API está rodando"""
    return jsonify({'success': True, 'message': 'API está online'}), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas dos tickets"""
    try:
        tickets = get_all_tickets()
        total = len(tickets)
        open_tickets = len([t for t in tickets if t.get('status') == 'open'])
        closed_tickets = total - open_tickets
        open_percentage = round((open_tickets / total * 100) if total > 0 else 0)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_tickets': total,
                'open_tickets': open_tickets,
                'closed_tickets': closed_tickets,
                'open_percentage': open_percentage
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    """Retorna todos os tickets"""
    try:
        tickets = get_all_tickets()
        return jsonify({'success': True, 'tickets': tickets}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tickets/<ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    """Retorna um ticket específico"""
    try:
        ticket = ticket_manager.get_ticket(ticket_id)
        if ticket:
            return jsonify({'success': True, 'ticket': ticket}), 200
        return jsonify({'success': False, 'error': 'Ticket não encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/create', methods=['POST'])
def create_ticket():
    """Cria um novo ticket"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        reason = data.get('reason', 'Sem motivo especificado')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id é obrigatório'}), 400
        
        ticket = ticket_manager.create_ticket(user_id, reason)
        return jsonify({
            'success': True, 
            'message': 'Ticket criado com sucesso',
            'ticket_number': ticket.get('number'),
            'ticket': ticket
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/close', methods=['POST'])
def close_ticket(ticket_id):
    """Fecha um ticket via API do bot"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Fechado via painel web')
        
        result = call_bot_api(f'/close/{ticket_id}', 'POST', {'reason': reason})
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro desconhecido')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/add-member', methods=['POST'])
def add_member(ticket_id):
    """Adiciona um membro ao ticket via API do bot"""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        
        if not member_id:
            return jsonify({'success': False, 'error': 'member_id é obrigatório'}), 400
        
        # Validar se é um ID numérico válido
        try:
            member_id = int(member_id)
        except ValueError:
            return jsonify({'success': False, 'error': 'member_id deve ser um número válido'}), 400
        
        result = call_bot_api(f'/add-member/{ticket_id}', 'POST', {'member_id': member_id})
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro desconhecido')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/notify', methods=['POST'])
def notify_staff(ticket_id):
    """Notifica a equipe sobre um ticket via API do bot"""
    try:
        result = call_bot_api(f'/notify/{ticket_id}', 'POST')
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message')
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro desconhecido')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== SERVIR HTML ====================

@app.route('/', methods=['GET'])
def serve_index():
    """Serve o arquivo index.html"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '''
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🤖 iBot - Painel de Controle</h1>
            <p>Arquivo index.html não encontrado.</p>
            <p><a href="/api/health">Verificar API</a></p>
        </body>
        </html>
        ''', 404

# ==================== TRATAMENTO DE ERROS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint não encontrado'}), 404

# ==================== ENDPOINTS DE ANÚNCIOS ====================

@app.route('/api/announcement/send', methods=['POST'])
def send_announcement():
    """Envia um anúncio para o canal do Discord"""
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'success': False, 'error': 'Mensagem é obrigatória'}), 400
        
        result = call_bot_api('/announcement/send', 'POST', {'message': message})
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Anúncio enviado com sucesso!'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro ao enviar anúncio')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ENDPOINTS DE CONTAS ====================

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Retorna todas as contas disponíveis"""
    try:
        accounts = load_accounts()
        return jsonify({'success': True, 'accounts': accounts}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/account/add', methods=['POST'])
def add_account():
    """Adiciona uma nova conta e posta no Discord"""
    try:
        data = request.get_json()
        
        # Validações
        required_fields = ['title', 'description', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} é obrigatório'}), 400
        
        accounts = load_accounts()
        
        # Cria nova conta
        account_id = f"account_{len(accounts) + 1}"
        new_account = {
            'id': account_id,
            'title': data['title'],
            'description': data['description'],
            'price': data['price'],
            'image_url': data.get('image_url', ''),
            'additional_info': data.get('additional_info', ''),
            'created_at': datetime.now().isoformat(),
            'available': True
        }
        
        accounts.append(new_account)
        save_accounts(accounts)
        
        # Envia para o Discord
        result = call_bot_api('/account/post', 'POST', new_account)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Conta adicionada e anunciada no Discord!',
                'account': new_account
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erro ao postar no Discord')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/account/<account_id>', methods=['DELETE'])
def delete_account(account_id):
    """Remove uma conta"""
    try:
        accounts = load_accounts()
        accounts = [acc for acc in accounts if acc['id'] != account_id]
        
        if save_accounts(accounts):
            return jsonify({
                'success': True,
                'message': 'Conta removida com sucesso!'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao salvar alterações'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/account/<account_id>/toggle', methods=['POST'])
def toggle_account_availability(account_id):
    """Alterna disponibilidade de uma conta"""
    try:
        accounts = load_accounts()
        
        for account in accounts:
            if account['id'] == account_id:
                account['available'] = not account.get('available', True)
                break
        
        if save_accounts(accounts):
            return jsonify({
                'success': True,
                'message': 'Disponibilidade atualizada!'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao salvar alterações'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== TRATAMENTO DE ERROS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("🌐 Iniciando painel web...")
    print("📡 Conectará com o bot na porta 5001")
    print("💡 Certifique-se de que o bot está rodando!")
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
