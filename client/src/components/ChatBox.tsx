import React, { useState, useRef, useEffect } from "react";
import axiosClient from "../config/AxiosClient";
import { AxiosProgressEvent } from "axios";

interface Message {
    role: "user" | "system";
    text: string;
}

interface StreamData {
    token?: string;
    state?: any;
}

const Chatbot: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([{ role: "system", text: "Good Evening Yahya. How may I assist you?" }]);
    const [input, setInput] = useState<string>("");
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [conversationState, setConversationState] = useState({
        is_initail_prompt: true,
        confidence_threshold: 0.7,
        symptom_similarity_threshold: 0.7,
        asked_symptoms: [],
        excluded_candidates: [],
        depth: 0,
        max_depth: 5,
        initial_prompt: input,
    });

    const chatContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim()) return;

        setMessages((prev) => [...prev, { role: "user", text: input }]);
        setInput("");
        setIsLoading(true);
        setMessages((prev) => [...prev, { role: "system", text: "" }]);

        let currentIndex = 0;
        let buffer = "";

        try {
            await axiosClient.post(
                "/chat",
                { message: input, state: conversationState },
                {
                    responseType: "text",
                    onDownloadProgress: (progressEvent: AxiosProgressEvent) => {
                        setIsLoading(false);
                        const evt = progressEvent.event;
                        const target = evt.currentTarget as XMLHttpRequest;
                        const responseText = target.response as string;
                        const newChunk = responseText.substring(currentIndex);
                        currentIndex = responseText.length;
                        buffer += newChunk;

                        const lines = buffer.split("\n");
                        buffer = lines.pop() || "";

                        lines.forEach((line: string) => {
                            if (line.startsWith("data: ")) {
                                const jsonStr = line.replace("data: ", "");
                                try {
                                    const data: StreamData = JSON.parse(jsonStr);
                                    if (data.token) {
                                        setMessages((prev) => {
                                            const lastMsg = prev[prev.length - 1];
                                            if (lastMsg && lastMsg.role === "system") {
                                                return [
                                                    ...prev.slice(0, prev.length - 1),
                                                    { ...lastMsg, text: lastMsg.text + data.token },
                                                ];
                                            }
                                            return prev;
                                        });
                                    }
                                    if (data.state) {
                                        setConversationState({
                                            ...data.state,
                                            is_initail_prompt: false,
                                        });
                                    }
                                } catch (err) {
                                    console.error("Error parsing streamed JSON", err);
                                }
                            }
                        });
                    },
                }
            );
        } catch (error) {
            console.error("Error during chat request:", error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50 p-4 gap-2">
            <div
                ref={chatContainerRef}
                className="flex-1 overflow-y-auto p-4 space-y-4 bg-white shadow-lg rounded-xl border border-gray-200 relative"
                style={{
                    backgroundImage: "url('/wallpaper.jpg')",
                    backgroundSize: "auto",
                    backgroundPosition: "center",
                    backgroundRepeat: "no-repeat",
                }}
            >
                {messages.map((msg, index) => (
                    <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        {msg.text && (
                            <div
                                className={`max-w-xs md:max-w-md px-4 py-2 rounded-lg shadow backdrop-blur-lg bg-opacity-70 ${
                                    msg.role === "user" ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-900"
                                }`}
                            >
                                <div dangerouslySetInnerHTML={{ __html: msg.text }} />
                            </div>
                        )}
                    </div>
                ))}
                {isLoading && (
                    <div className="flex justify-start">
                        <img src="/typing-dots.gif" alt="Loading..." className="w-32 h-20 mr-2" />
                    </div>
                )}
            </div>
            <div className="flex items-center gap-2">
                <input
                    type="text"
                    className="flex-1 border border-gray-300 rounded-full px-4 py-2 shadow-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                    placeholder="Type your message..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") sendMessage();
                    }}
                    disabled={isLoading}
                />
                <button
                    onClick={sendMessage}
                    className={`px-4 py-2 rounded-full shadow-md transition-all ${
                        isLoading ? "bg-gray-400 cursor-not-allowed" : "bg-blue-500 hover:bg-blue-600 text-white"
                    }`}
                    disabled={isLoading}
                >
                    Send
                </button>
            </div>
        </div>
    );
};

export default Chatbot;
