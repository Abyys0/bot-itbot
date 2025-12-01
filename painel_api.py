from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Funções para gerenciar tickets sem bot
def load_tickets():
    """Carrega tickets do arquivo JSON"""
    try:
        if os.path.exists('tickets.json'):
            with open('tickets.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception:
        return []

def get_all_tickets():
    """Retorna todos os tickets"""
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
    """Fecha um ticket"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Sem motivo especificado')
        
        success = ticket_manager.close_ticket(ticket_id, reason)
        if success:
            return jsonify({
                'success': True,
                'message': 'Ticket fechado com sucesso'
            }), 200
        return jsonify({'success': False, 'error': 'Ticket não encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/add-member', methods=['POST'])
def add_member(ticket_id):
    """Adiciona um membro a um ticket"""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        
        if not member_id:
            return jsonify({'success': False, 'error': 'member_id é obrigatório'}), 400
        
        ticket = ticket_manager.get_ticket(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket não encontrado'}), 404
        
        # Adiciona o membro à lista
        if 'members' not in ticket:
            ticket['members'] = []
        if member_id not in ticket['members']:
            ticket['members'].append(member_id)
            ticket_manager.update_ticket(ticket_id, ticket)
        
        return jsonify({
            'success': True,
            'message': f'Membro {member_id} adicionado ao ticket'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ticket/<ticket_id>/notify', methods=['POST'])
def notify_staff(ticket_id):
    """Notifica a equipe sobre um ticket"""
    try:
        ticket = ticket_manager.get_ticket(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket não encontrado'}), 404
        
        # Aqui você pode integrar com Discord para enviar notificação
        # Por enquanto, apenas retorna sucesso
        
        return jsonify({
            'success': True,
            'message': f'Equipe notificada sobre ticket #{ticket.get("number")}'
        }), 200
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

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
