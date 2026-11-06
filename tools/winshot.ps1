# Captura a janela do PPSSPP (mesmo atras de outras janelas) para um PNG.
param([string]$Out)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W32 {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
# Sem isso, com escala do Windows acima de 100%, o retangulo vem em pixels logicos e o print sai cortado.
[void][W32]::SetProcessDPIAware()
$p = Get-Process PPSSPPWindows64 | Select-Object -First 1
# Janela minimizada tem area zero: restaura sem roubar o foco.
if ([W32]::IsIconic($p.MainWindowHandle)) { [void][W32]::ShowWindow($p.MainWindowHandle, 4); Start-Sleep -Milliseconds 500 }
$r = New-Object W32+RECT
[void][W32]::GetClientRect($p.MainWindowHandle, [ref]$r)
$bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$dc = $g.GetHdc()
[void][W32]::PrintWindow($p.MainWindowHandle, $dc, 3)
$g.ReleaseHdc($dc)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
"$($bmp.Width)x$($bmp.Height)"
