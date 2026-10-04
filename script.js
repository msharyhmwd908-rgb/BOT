function goToPage2() {
    document.getElementById('page1').classList.remove('active');
    document.getElementById('page2').classList.add('active');
}

function registerUser() {
    // Client ID الخاص ببوتك
    const clientId = '1548502443636035774'; 
    
    // الرابط الرسمي الجديد والمربوط باستضافتك
    const redirectUri = encodeURIComponent('https://bot-najm.apps.bot-hosting.cloud/callback'); 
    
    // التوجيه لصفحة تسجيل الدخول الرسمية في ديسكورد
    window.location.href = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=identify%20guilds`;
}

