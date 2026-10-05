import ChatbotName from "../components/branding/ChatbotName";
import NewChatButton from "../components/chat/NewChatButton";

export default function Home() {
  return (
    <div className="empty-chat-container">
      <section className="empty-chat">
        <div className="chat-avatar large-avatar" aria-hidden="true">AI</div>
        <h1>Chatbot <ChatbotName /></h1>
        <p>V4.2 · Tạo cuộc trò chuyện mới hoặc chọn lịch sử riêng của bạn.</p>
        <div className="empty-chat-action">
          <NewChatButton />
        </div>
      </section>
    </div>
  );
}
