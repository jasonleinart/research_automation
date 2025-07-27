#!/usr/bin/env python3
"""
CLI interface for chatting with the research agent about papers.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import db_manager
from src.database.paper_repository import PaperRepository
from src.services.conversation_service import ConversationService
from src.services.author_service import AuthorService


class PaperChatCLI:
    """Command-line interface for paper conversations."""
    
    def __init__(self):
        self.conversation_service = ConversationService()
        self.paper_repo = PaperRepository()
        self.author_service = AuthorService()
        self.current_session = None
    
    async def initialize(self):
        """Initialize database connection."""
        await db_manager.initialize()
        print("🤖 Research Agent initialized!")
    
    async def list_papers(self):
        """List available papers for selection."""
        papers = await self.paper_repo.list_all()
        
        if not papers:
            print("❌ No papers found in database. Please ingest some papers first.")
            return []
        
        print(f"\n📚 Available Papers ({len(papers)}):")
        print("-" * 80)
        
        for i, paper in enumerate(papers, 1):
            # Load authors for display
            paper_with_authors = await self.author_service.get_paper_with_authors(paper.id)
            authors = ', '.join(paper_with_authors.author_names) if paper_with_authors.author_names else 'Unknown'
            paper_type = paper.paper_type.value if paper.paper_type else 'Unknown'
            
            print(f"{i:2d}. {paper.title}")
            print(f"    Authors: {authors}")
            print(f"    Type: {paper_type}")
            if paper.arxiv_id:
                print(f"    ArXiv: {paper.arxiv_id}")
            print()
        
        return papers
    
    async def select_paper(self, papers):
        """Let user select a paper to discuss."""
        while True:
            try:
                choice = input(f"Select a paper (1-{len(papers)}) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                paper_index = int(choice) - 1
                if 0 <= paper_index < len(papers):
                    return papers[paper_index]
                else:
                    print(f"Please enter a number between 1 and {len(papers)}")
                    
            except ValueError:
                print("Please enter a valid number or 'q' to quit")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                return None
    
    async def start_conversation(self, paper):
        """Start a conversation about the selected paper."""
        # Create new conversation session
        self.current_session = self.conversation_service.create_session()
        
        # Set paper context
        success = await self.conversation_service.set_paper_context(
            self.current_session.session_id, 
            paper.id
        )
        
        if not success:
            print("❌ Failed to set paper context")
            return
        
        print(f"\n🎯 Now chatting about: {paper.title}")
        print("💡 You can ask questions about the paper, its authors, related work, or anything else!")
        print("💬 Type 'help' for suggestions, 'switch' to change papers, or 'quit' to exit")
        print("-" * 80)
        
        # Start chat loop
        await self.chat_loop()
    
    async def chat_loop(self):
        """Main chat interaction loop."""
        while True:
            try:
                # Get user input
                user_input = input("\n🧑 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Thanks for chatting! Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                
                elif user_input.lower() == 'switch':
                    print("🔄 Switching papers...")
                    await self.run()  # Restart paper selection
                    break
                
                elif user_input.lower() == 'context':
                    self.show_context()
                    continue
                
                elif user_input.lower() == 'history':
                    self.show_history()
                    continue
                
                # Process message with conversation service
                print("🤖 Agent: ", end="", flush=True)
                response = await self.conversation_service.send_message(
                    self.current_session.session_id,
                    user_input
                )
                
                if response:
                    print(response)
                else:
                    print("Sorry, I couldn't process your message. Please try again.")
                
            except KeyboardInterrupt:
                print("\n👋 Thanks for chatting! Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print("Please try again or type 'quit' to exit.")
    
    def show_help(self):
        """Show help information."""
        print("\n💡 Here are some things you can ask me:")
        print("• 'What is this paper about?' - Get a summary")
        print("• 'Who are the authors?' - Learn about the authors")
        print("• 'What type of paper is this?' - Get the paper classification")
        print("• 'Are there related papers?' - Find connections in your database")
        print("• 'What are the key contributions?' - Understand the main findings")
        print("• 'Explain [concept]' - Get explanations of specific concepts")
        print("\n🔧 Commands:")
        print("• 'help' - Show this help")
        print("• 'context' - Show current paper context")
        print("• 'history' - Show conversation history")
        print("• 'switch' - Change to a different paper")
        print("• 'quit' - Exit the chat")
    
    def show_context(self):
        """Show current conversation context."""
        if not self.current_session:
            print("❌ No active conversation session")
            return
        
        summary = self.conversation_service.get_session_summary(self.current_session.session_id)
        if summary:
            print(f"\n📋 Conversation Context:")
            print(f"Session ID: {summary['session_id'][:8]}...")
            print(f"Current paper: {summary['current_paper']}")
            print(f"Messages exchanged: {summary['message_count']}")
            print(f"Related papers found: {summary['related_papers_count']}")
            print(f"Started: {summary['created_at']}")
    
    def show_history(self):
        """Show conversation history."""
        if not self.current_session:
            print("❌ No active conversation session")
            return
        
        messages = self.current_session.get_recent_messages(10)
        if not messages:
            print("📝 No conversation history yet")
            return
        
        print(f"\n📝 Recent Conversation History:")
        print("-" * 60)
        
        for msg in messages:
            if msg.role == 'user':
                print(f"🧑 You: {msg.content}")
            elif msg.role == 'assistant':
                print(f"🤖 Agent: {msg.content}")
            elif msg.role == 'system':
                print(f"ℹ️  System: {msg.content}")
            print()
    
    async def run(self):
        """Main application loop."""
        try:
            await self.initialize()
            
            # List available papers
            papers = await self.list_papers()
            if not papers:
                return
            
            # Let user select a paper
            selected_paper = await self.select_paper(papers)
            if not selected_paper:
                return
            
            # Start conversation about selected paper
            await self.start_conversation(selected_paper)
            
        except Exception as e:
            print(f"❌ Application error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Entry point for the CLI application."""
    print("🚀 Research Agent - Paper Chat Interface")
    print("=" * 50)
    
    cli = PaperChatCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())