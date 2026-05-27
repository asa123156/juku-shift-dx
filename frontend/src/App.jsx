// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// 作成したページコンポーネントを読み込む
import Login from './pages/Login';
import StudentShift from './pages/StudentShift';
import AdminDashboard from './pages/AdminDashboard';

export default function App() {
  return (
    // BrowserRouterでアプリ全体を囲むことで画面遷移が可能になる
    <BrowserRouter>
      <Routes>
        {/* URLと表示する画面の紐付け（ルーティング設定） */}
        <Route path="/" element={<Login />} />
        <Route path="/student" element={<StudentShift />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}