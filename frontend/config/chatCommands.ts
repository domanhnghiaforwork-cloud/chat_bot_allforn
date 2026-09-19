export const CHAT_COMMANDS = [
  {
    name: "/token",
    description: "Xem số token hiện tại của cuộc hội thoại",
  },
  {
    name: "/context",
    description: "Xem context window và ngân sách input/output của chat",
  },
] as const;

export type ChatCommandName = (typeof CHAT_COMMANDS)[number]["name"];

export function isChatCommandName(value: string): value is ChatCommandName {
  return CHAT_COMMANDS.some((command) => command.name === value);
}
