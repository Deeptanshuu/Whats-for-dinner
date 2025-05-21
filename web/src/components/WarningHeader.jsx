const WarningHeader = () => {
    return (
        <div className="bg-yellow-500 text-white text-center py-3 text-xl">
            <strong>Warning:</strong> Server is offline and not reachable. Please check your internet connection or try again later.
        </div>
    );
};

export default WarningHeader;