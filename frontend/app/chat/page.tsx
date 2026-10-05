import ChatbotName from "../../components/branding/ChatbotName";
import NewChatButton from "../../components/chat/NewChatButton";

export default function ChatHomePage() {
  return (
    <div className="empty-chat-container">
      <section className="empty-chat">
        <div className="chat-avatar large-avatar" aria-hidden="true">AI</div>
        <h1>Chatbot <ChatbotName /></h1>
        <p>Bắt đầu cuộc trò chuyện mới để hỏi đáp hoặc chọn một đoạn chat từ lịch sử bên trái.</p>
        <div className="empty-chat-action">
          <NewChatButton />
        </div>
      </section>
    </div>
  );
}

