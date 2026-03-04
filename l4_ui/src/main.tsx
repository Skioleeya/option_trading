import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './components/App'
import { injectSmokeTester } from './smoke_test'
import './index.css'

injectSmokeTester()

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
)
