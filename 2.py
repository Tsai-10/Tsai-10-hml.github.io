<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>生活便民地圖</title>

  <!-- Bootstrap -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

  <!-- Font Awesome Icons -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">

  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />

  <style>
    body {
      font-family: "Noto Sans TC", sans-serif;
      background-color: #f8f9fa;
    }

    /* Navbar */
    .navbar {
      background-color: #343a40;
    }
    .navbar a {
      color: white;
    }

    /* Hero Section */
    .hero {
      background: linear-gradient(to right, #74ebd5, #acb6e5);
      color: white;
      text-align: center;
      padding: 100px 20px;
    }
    .hero h1 {
      font-size: 3rem;
      font-weight: bold;
    }
    .hero p {
      font-size: 1.2rem;
    }

    /* Map */
    #map {
      height: 70vh;
      width: 100%;
      margin-top: 30px;
      border-radius: 15px;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    /* Footer */
    footer {
      text-align: center;
      padding: 15px;
      margin-top: 20px;
      background: #343a40;
      color: white;
    }
  </style>
</head>
<body>

  <!-- 導覽列 -->
  <nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container">
      <a class="navbar-brand" href="#">生活便民地圖</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item"><a class="nav-link" href="#features">專案介紹</a></li>
          <li class="nav-item"><a class="nav-link" href="#map-section">地圖展示</a></li>
          <li class="nav-item"><a class="nav-link" href="#contact">聯絡我們</a></li>
        </ul>
      </div>
    </div>
  </nav>

  <!-- Hero 區塊 -->
  <section class="hero">
    <h1>生活便民地圖</h1>
    <p>輕鬆找到最近的飲水機、廁所、垃圾桶、公用插座</p>
    <a href="https://tsai-10-hmlappio-e3uyd4wnbhhfgthkgrfab2.streamlit.app/" 
       target="_blank" 
       rel="noopener noreferrer" 
       class="btn btn-light btn-lg mt-3">
      <i class="fas fa-external-link-alt me-2"></i> 查看專題作品
    </a>
  </section>

  <!-- 專案特色 -->
  <section id="features" class="container my-5">
    <div class="row text-center">
      <div class="col-md-4">
        <i class="fas fa-map-marked-alt fa-3x mb-3 text-primary"></i>
        <h4>智慧定位</h4>
        <p>自動定位使用者位置，提供最佳化的附近設施搜尋體驗。</p>
      </div>
      <div class="col-md-4">
        <i class="fas fa-filter fa-3x mb-3 text-success"></i>
        <h4>類別篩選</h4>
        <p>輕鬆篩選飲水機、廁所、垃圾桶等不同類型設施。</p>
      </div>
      <div class="col-md-4">
        <i class="fas fa-comments fa-3x mb-3 text-warning"></i>
        <h4>回饋系統</h4>
        <p>使用者可提交回饋，補充或修正設施位置資訊。</p>
      </div>
    </div>
  </section>

  <!-- 地圖展示 -->
  <section id="map-section" class="container">
    <h2 class="text-center my-4">地圖展示</h2>
    <div id="map"></div>
  </section>

  <!-- Footer -->
  <footer>
    <p>© 2025 生活便民地圖 專題組</p>
  </footer>

  <!-- JS Libraries -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

  <script>
    // 初始化地圖，中心點設定為台科大
    var map = L.map('map').setView([25.0135, 121.5418], 15);

    // Carto Positron 樣式 - 乾淨高級展示風格
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> 貢獻者 &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(map);

    // 範例標記：台科大
    L.marker([25.0135, 121.5418]).addTo(map)
      .bindPopup("<b>台灣科技大學</b><br>生活便民地圖專題展示");

    // 其他範例點位
    L.marker([25.0173, 121.5400]).addTo(map).bindPopup("公用飲水機");
    L.marker([25.0150, 121.5430]).addTo(map).bindPopup("公共廁所");
  </script>
</body>
</html>
