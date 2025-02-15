import React from "react";

const Topbar: React.FC = () => {
    return (
        <div className="w-full bg-blue-500 text-white py-3 px-6 shadow-md flex items-center justify-between">
            {/* Logo and Name */}
            <div className="flex items-center gap-3">
                <img
                    src="/chatbot-avatar.avif" // Replace with actual avatar image path
                    alt="Doctor Avatar"
                    className="w-10 h-10 rounded-full border-2 border-white"
                />
                <h1 className="text-lg font-semibold">Doctor Saab</h1>
            </div>
        </div>
    );
};

export default Topbar;

