export function Input({ type = "text", ...props }) {
    return (
      <input
        type={type}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-black"
        {...props}
      />
    );
  }
  