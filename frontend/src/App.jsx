// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Login from './pages/Login';
import StudentShift from './pages/StudentShift';
import AdminDashboard from './pages/AdminDashboard';
// ★インポート画面を読み込む
import DataImport from './pages/DataImport'; 

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/student" element={<StudentShift />} />
        <Route path="/admin" element={<AdminDashboard />} />
        {/* ★インポート画面のURLを設定 */}
        <Route path="/import" element={<DataImport />} /> 
      </Routes>
    </BrowserRouter>
  );
}