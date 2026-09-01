/**
 * Hand-authored SVG art for the login page.
 *
 * Everything here is inline SVG on purpose: the login screen is eagerly
 * loaded and is the app's first paint, so it must not wait on a raster
 * image, an icon library, or a web font. Every piece carries an explicit
 * viewBox and is sized by its container, so nothing reflows as the page
 * settles.
 */

const NAVY = "#26346B";
const NAVY_DEEP = "#1B2550";
const YELLOW = "#F5B301";
const SKIN = "#F3C6A5";
const CORAL = "#E8705A";
const TEAL = "#BFE3E0";
const GREEN = "#4CA57A";
const PEACH = "#FDEDE4";

/* ------------------------------------------------------------------ */
/* Logo — graduation cap crossed by a pencil                           */
/* ------------------------------------------------------------------ */

export function Logo({ className = "" }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width="56"
      height="56"
      className={className}
      role="img"
      aria-label="EduConnect AI"
    >
      {/* mortarboard underside */}
      <path d="M18 27v9c0 4 6.3 7 14 7s14-3 14-7v-9l-14 6.5L18 27Z" fill={NAVY_DEEP} />
      {/* mortarboard top */}
      <path d="M32 9 60 22 32 35 4 22 32 9Z" fill={NAVY} />
      {/* tassel cord */}
      <path d="M57 23.5v9" stroke={NAVY_DEEP} strokeWidth="2" strokeLinecap="round" />

      {/* pencil, crossing from lower-right up through the cap */}
      <g transform="rotate(38 40 40)">
        <rect x="33" y="26" width="9" height="24" fill={SKIN} />
        <rect x="33" y="26" width="3" height="24" fill="#E0AC85" />
        <rect x="33" y="20" width="9" height="6" fill={YELLOW} />
        <path d="M33 50h9l-4.5 8L33 50Z" fill={NAVY_DEEP} />
      </g>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Backdrop — organic yellow shapes bleeding off two corners           */
/* ------------------------------------------------------------------ */

export function BackdropBlobs() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* top-right */}
      <svg
        viewBox="0 0 400 320"
        className="absolute -right-24 -top-28 h-[340px] w-[420px] sm:-right-16 sm:h-[380px] sm:w-[470px]"
        preserveAspectRatio="xMidYMid meet"
      >
        <path
          d="M400 0v210c-52 34-118 22-176-6-62-30-124-72-118-128C112 20 178 4 240 0h160Z"
          fill={YELLOW}
        />
      </svg>

      {/* bottom-left */}
      <svg
        viewBox="0 0 400 320"
        className="absolute -bottom-28 -left-28 h-[320px] w-[400px] sm:-bottom-20 sm:h-[360px] sm:w-[440px]"
        preserveAspectRatio="xMidYMid meet"
      >
        <path
          d="M0 320V96c46-40 112-34 172-8 64 28 128 74 120 132-8 56-74 84-138 100H0Z"
          fill={YELLOW}
          opacity="0.92"
        />
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Illustration — study room. Desktop only.                            */
/* ------------------------------------------------------------------ */

export function StudyScene({ className = "" }) {
  return (
    <svg
      viewBox="0 0 520 400"
      className={className}
      role="img"
      aria-label="Students and staff working at desks"
    >
      {/* soft backdrop */}
      <path
        d="M46 92c40-58 132-84 214-72 84 12 156 58 178 118 22 62-18 132-96 158-84 28-206 24-268-18C10 234-2 154 46 92Z"
        fill={PEACH}
      />

      {/* window */}
      <g>
        <rect x="52" y="70" width="96" height="86" rx="6" fill={TEAL} />
        <rect
          x="52" y="70" width="96" height="86" rx="6"
          fill="none" stroke={NAVY} strokeWidth="3.5"
        />
        <path d="M100 70v86M52 113h96" stroke={NAVY} strokeWidth="3" />
      </g>

      {/* shelf + books */}
      <g>
        <rect x="300" y="104" width="86" height="4.5" rx="2" fill={NAVY} />
        <rect x="308" y="82" width="9" height="22" rx="2" fill={CORAL} />
        <rect x="319" y="86" width="9" height="18" rx="2" fill={YELLOW} />
        <rect x="330" y="79" width="9" height="25" rx="2" fill={NAVY} />
        <rect x="341" y="88" width="9" height="16" rx="2" fill={GREEN} />
      </g>

      {/* floor */}
      <path d="M18 330h484" stroke={NAVY} strokeWidth="3" strokeLinecap="round" />

      {/* ---- seated figure, left ---- */}
      <g>
        <rect x="58" y="256" width="112" height="6" rx="3" fill={NAVY} />
        <path d="M68 262v58M160 262v58" stroke={NAVY} strokeWidth="5" strokeLinecap="round" />
        {/* laptop */}
        <path d="M96 232h40l6 22H90l6-22Z" fill="#FFFFFF" stroke={NAVY} strokeWidth="3" />
        <rect x="86" y="252" width="60" height="5" rx="2.5" fill={NAVY} />
        {/* body */}
        <path d="M74 256v-30c0-13 9-22 22-22h4v52H74Z" fill={CORAL} />
        <rect x="60" y="286" width="42" height="12" rx="6" fill={NAVY_DEEP} />
        <path d="M66 298v22" stroke={NAVY_DEEP} strokeWidth="7" strokeLinecap="round" />
        <circle cx="88" cy="188" r="15" fill={SKIN} />
        <path d="M73 186c0-11 7-17 15-17s15 6 15 17c-6-4-10-6-15-6s-9 2-15 6Z" fill={NAVY_DEEP} />
        {/* chair back */}
        <path d="M56 250v-46" stroke={NAVY} strokeWidth="5" strokeLinecap="round" />
      </g>

      {/* ---- standing figure, centre ---- */}
      <g>
        <rect x="196" y="218" width="120" height="6" rx="3" fill={NAVY} />
        <path d="M206 224v106M306 224v106" stroke={NAVY} strokeWidth="5" strokeLinecap="round" />
        {/* laptop */}
        <path d="M232 194h44l7 24h-58l7-24Z" fill="#FFFFFF" stroke={NAVY} strokeWidth="3" />
        <rect x="222" y="216" width="66" height="5" rx="2.5" fill={NAVY} />
        {/* body */}
        <path d="M242 218v-40c0-14 10-24 24-24s24 10 24 24v40h-48Z" fill="#5B8FD9" />
        <path d="M250 218v112M282 218v112" stroke={NAVY_DEEP} strokeWidth="9" strokeLinecap="round" />
        <circle cx="266" cy="136" r="16" fill={SKIN} />
        <path d="M250 134c0-12 7-19 16-19s16 7 16 19c-6-5-10-7-16-7s-10 2-16 7Z" fill={NAVY_DEEP} />
      </g>

      {/* ---- seated figure, right ---- */}
      <g>
        <rect x="348" y="256" width="112" height="6" rx="3" fill={NAVY} />
        <path d="M358 262v58M450 262v58" stroke={NAVY} strokeWidth="5" strokeLinecap="round" />
        <path d="M386 232h40l6 22h-52l6-22Z" fill="#FFFFFF" stroke={NAVY} strokeWidth="3" />
        <rect x="376" y="252" width="60" height="5" rx="2.5" fill={NAVY} />
        <path d="M436 256v-30c0-13-9-22-22-22h-4v52h26Z" fill={YELLOW} />
        <rect x="408" y="286" width="42" height="12" rx="6" fill={NAVY_DEEP} />
        <path d="M444 298v22" stroke={NAVY_DEEP} strokeWidth="7" strokeLinecap="round" />
        <circle cx="422" cy="188" r="15" fill={SKIN} />
        <path d="M407 186c0-11 7-17 15-17s15 6 15 17c-6-4-10-6-15-6s-9 2-15 6Z" fill="#7A4A2B" />
        <path d="M462 250v-46" stroke={NAVY} strokeWidth="5" strokeLinecap="round" />
      </g>

      {/* plant */}
      <g>
        <path d="M478 330v-34" stroke={NAVY} strokeWidth="3.5" strokeLinecap="round" />
        <path d="M478 300c-16-4-24-16-22-30 14-2 24 8 26 22" fill={GREEN} />
        <path d="M478 292c12-8 16-22 10-34-13 4-19 16-18 30" fill="#3E8C68" />
        <path d="M466 330h26l-4 22h-18l-4-22Z" fill={CORAL} />
      </g>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Input icons                                                         */
/* ------------------------------------------------------------------ */

export function MailIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" className={className} aria-hidden="true">
      <rect
        x="2.75" y="5" width="18.5" height="14" rx="3"
        fill="none" stroke="currentColor" strokeWidth="1.8"
      />
      <path
        d="m4 8 6.9 4.9a2 2 0 0 0 2.2 0L20 8"
        fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
      />
    </svg>
  );
}

export function KeyIcon({ className = "" }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" className={className} aria-hidden="true">
      <circle cx="8" cy="12" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M12.25 12H21m-3 0v3.2M15.4 12v2.4"
        fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
      />
    </svg>
  );
}
