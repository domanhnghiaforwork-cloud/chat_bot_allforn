import ChatbotName from "../components/branding/ChatbotName";

export default function Home() {
  return (
    <section className="empty-chat">
      <div className="chat-avatar" aria-hidden="true">AI</div>
      <h1>Chatbot <ChatbotName /></h1>
      <p>V4.2 · Tạo cuộc trò chuyện mới hoặc chọn lịch sử riêng của bạn.</p>
    </section>
  );
}
