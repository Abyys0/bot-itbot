"""
Sistema de Pagamento PIX
Gerencia pagamentos via PIX com código copia e cola
"""
import json
import os
from datetime import datetime
import uuid

class PixManager:
    """Gerencia pagamentos PIX"""
    
    def __init__(self):
        self.payments_file = "payments.json"
        self.config_file = "pix_config.json"
        self.load_payments()
        self.load_config()
    
    def load_config(self):
        """Carrega configuração do PIX"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            # Configuração padrão
            self.config = {
                "pix_key": "",  # Chave PIX (CPF, email, telefone ou chave aleatória)
                "pix_name": "",  # Nome do beneficiário
                "pix_city": "",  # Cidade do beneficiário
                "enabled": False
            }
            self.save_config()
    
    def save_config(self):
        """Salva configuração do PIX"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def update_config(self, pix_key: str, pix_name: str, pix_city: str = "SAO PAULO"):
        """Atualiza configuração do PIX"""
        self.config = {
            "pix_key": pix_key,
            "pix_name": pix_name,
            "pix_city": pix_city,
            "enabled": True
        }
        self.save_config()
        return True
    
    def load_payments(self):
        """Carrega pagamentos do arquivo JSON"""
        if os.path.exists(self.payments_file):
            with open(self.payments_file, 'r', encoding='utf-8') as f:
                self.payments = json.load(f)
        else:
            self.payments = {}
    
    def save_payments(self):
        """Salva pagamentos no arquivo JSON"""
        with open(self.payments_file, 'w', encoding='utf-8') as f:
            json.dump(self.payments, f, indent=4, ensure_ascii=False)
    
    def generate_pix_code(self, amount: float, description: str = "Compra de conta"):
        """
        Gera código PIX copia e cola (simplificado)
        Nota: Para produção, use uma API de pagamento real como Mercado Pago, PagSeguro, etc.
        """
        if not self.config.get("enabled") or not self.config.get("pix_key"):
            return None, "PIX não configurado. Configure a chave PIX primeiro."
        
        # Por enquanto, retorna instruções de pagamento manual
        # Em produção, você deve integrar com uma API de pagamento
        pix_info = {
            "pix_key": self.config["pix_key"],
            "amount": amount,
            "name": self.config["pix_name"],
            "city": self.config["pix_city"],
            "description": description
        }
        
        return pix_info, "PIX gerado com sucesso"
    
    def create_payment(self, user_id: str, account_id: str, amount: float, account_title: str):
        """Cria um novo pagamento pendente"""
        payment_id = str(uuid.uuid4())[:8]  # ID único curto
        
        pix_info, message = self.generate_pix_code(amount, f"Compra: {account_title}")
        
        if not pix_info:
            return None, message
        
        payment_data = {
            "payment_id": payment_id,
            "user_id": user_id,
            "account_id": account_id,
            "account_title": account_title,
            "amount": amount,
            "pix_key": pix_info["pix_key"],
            "status": "pending",  # pending, confirmed, cancelled
            "created_at": datetime.now().isoformat(),
            "confirmed_at": None,
            "confirmed_by": None
        }
        
        self.payments[payment_id] = payment_data
        self.save_payments()
        
        return payment_data, "Pagamento criado com sucesso"
    
    def confirm_payment(self, payment_id: str, staff_id: str):
        """Confirma um pagamento"""
        if payment_id not in self.payments:
            return False, "Pagamento não encontrado"
        
        if self.payments[payment_id]["status"] == "confirmed":
            return False, "Pagamento já foi confirmado anteriormente"
        
        self.payments[payment_id]["status"] = "confirmed"
        self.payments[payment_id]["confirmed_at"] = datetime.now().isoformat()
        self.payments[payment_id]["confirmed_by"] = staff_id
        self.save_payments()
        
        return True, "Pagamento confirmado com sucesso"
    
    def cancel_payment(self, payment_id: str):
        """Cancela um pagamento"""
        if payment_id not in self.payments:
            return False, "Pagamento não encontrado"
        
        if self.payments[payment_id]["status"] == "confirmed":
            return False, "Não é possível cancelar um pagamento já confirmado"
        
        self.payments[payment_id]["status"] = "cancelled"
        self.save_payments()
        
        return True, "Pagamento cancelado"
    
    def get_payment(self, payment_id: str):
        """Obtém informações de um pagamento"""
        return self.payments.get(payment_id)
    
    def get_user_payments(self, user_id: str):
        """Obtém todos os pagamentos de um usuário"""
        return [p for p in self.payments.values() if p["user_id"] == user_id]
    
    def get_pending_payments(self):
        """Obtém todos os pagamentos pendentes"""
        return [p for p in self.payments.values() if p["status"] == "pending"]
    
    def get_all_payments(self):
        """Retorna todos os pagamentos"""
        return list(self.payments.values())
    
    def is_configured(self):
        """Verifica se o PIX está configurado"""
        return self.config.get("enabled", False) and bool(self.config.get("pix_key"))
