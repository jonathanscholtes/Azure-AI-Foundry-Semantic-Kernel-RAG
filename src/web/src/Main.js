import React from "react";
import ChatApp from "./ChatApp";
import "./Main.css";

const App = () => {
  return (
    <div className="Main">
      <div className="Main-Header">
        <img src="/PolicyWise.png" alt="PolicyWise Logo" height="95%" />
      </div>

      <div className="Main-Content">
        <ChatApp />
      </div>

      <div className="Main-Footer">
        <b>Disclaimer: Sample Application</b>
          <br />
          Please note that this sample application is provided for demonstration
          purposes only and should not be used in production environments
          without proper validation and testing.
        </div>
    
    </div>
  );
};

export default App;