import discord
from discord.ext import commands
import json
import os

class TicketManager:
    """Gerencia o sistema de tickets"""
    
    def __init__(self, bot):
        self.bot = bot
        self.tickets_file = "tickets.json"
        self.load_tickets()
    
    def load_tickets(self):
        """Carrega tickets do arquivo JSON"""
        if os.path.exists(self.tickets_file):
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                self.tickets = json.load(f)
        else:
            self.tickets = {}
    
    def save_tickets(self):
        """Salva tickets no arquivo JSON"""
        with open(self.tickets_file, 'w', encoding='utf-8') as f:
            json.dump(self.tickets, f, indent=4, ensure_ascii=False)
    
    def create_ticket(self, user_id: int, ticket_number: int) -> str:
        """Cria um novo ticket"""
        ticket_id = f"ticket_{ticket_number}"
        self.tickets[ticket_id] = {
            "user_id": user_id,
            "ticket_number": ticket_number,
            "status": "open",
            "created_at": str(discord.utils.utcnow()),
            "channel_id": None
        }
        self.save_tickets()
        return ticket_id
    
    def close_ticket(self, ticket_id: str, staff_id: int):
        """Fecha um ticket"""
        if ticket_id in self.tickets:
            self.tickets[ticket_id]["status"] = "closed"
            self.tickets[ticket_id]["closed_by"] = staff_id
            self.save_tickets()
            return True
        return False
    
    def get_ticket(self, ticket_id: str):
        """Obtém informações de um ticket"""
        return self.tickets.get(ticket_id)
    
    def get_next_ticket_number(self) -> int:
        """Obtém o próximo número de ticket"""
        if not self.tickets:
            return 1
        return max(int(t.split('_')[1]) for t in self.tickets.keys()) + 1
    
    def set_ticket_channel(self, ticket_id: str, channel_id: int):
        """Define o channel ID do ticket"""
        if ticket_id in self.tickets:
            self.tickets[ticket_id]["channel_id"] = channel_id
            self.save_tickets()
