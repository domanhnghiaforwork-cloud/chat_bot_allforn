import ChatBox from "../../../components/ChatBox";

interface ChatPageProps {
  params: Promise<{ conversationId: string }>;
}

export default async function ChatPage({ params }: ChatPageProps) {
  const { conversationId } = await params;
  return <ChatBox conversationId={conversationId} />;
}
